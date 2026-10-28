"""End-to-end API tests that follow the UML sequence diagram:
register -> admin approves -> officer adds company + job -> student applies -> officer shortlists/places -> report."""
from datetime import timedelta

from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Admin, PlacementOfficer, Student, User
from placement.models import Application, Notification

PWD = 'Str0ng!Pass99'
PDF = b'%PDF-1.4 test resume'
import tempfile
TMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PlacementFlowTests(APITestCase):
    def setUp(self):
        self.admin = Admin.register(PWD, name='Admin', email='admin@x.edu')
        self.admin.approve()

    def login(self, email):
        r = self.client.post('/api/auth/login/', {'email': email, 'password': PWD})
        self.assertEqual(r.status_code, 200, r.data)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + r.data['token'])
        return r.data

    def logout_client(self):
        self.client.credentials()

    def register_student(self, email='s1@x.edu', roll='R1', cgpa=8.2, branch='CSE'):
        return self.client.post('/api/auth/register/student/', {
            'name': 'Stu', 'email': email, 'password': PWD, 'roll_no': roll, 'branch': branch,
            'cgpa': cgpa, 'phone': '9876543210', 'address': 'Thrissur'})

    def approved_officer(self):
        o = PlacementOfficer.register(PWD, name='PO', email='po@x.edu', department='TPO', phone='9876543210')
        o.approve()
        return o

    def approved_student(self, resume=True, **kw):
        self.register_student(**kw)
        u = User.objects.get(email=kw.get('email', 's1@x.edu'))
        u.approve()
        if resume:
            u.get_profile().attach_resume(ContentFile(PDF, name='cv.pdf'))
        return u

    # ---- auth / approval ----
    def test_registration_pending_then_admin_approval(self):
        self.assertEqual(self.register_student().status_code, 201)
        r = self.client.post('/api/auth/login/', {'email': 's1@x.edu', 'password': PWD})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data['code'], 'pending')
        self.login('admin@x.edu')
        pending = self.client.get('/api/admin/users/?status=pending').data
        self.assertEqual(len(pending), 1)
        self.assertEqual(self.client.post(f"/api/admin/users/{pending[0]['id']}/approve/").status_code, 200)
        self.logout_client()
        self.assertEqual(self.login('s1@x.edu')['user']['role'], 'student')

    def test_wrong_password_and_validation(self):
        self.assertEqual(self.client.post('/api/auth/login/', {'email': 'a@b.com', 'password': 'x'}).status_code, 400)
        bad = self.client.post('/api/auth/register/student/', {'name': 'x', 'email': 'bad', 'password': '123',
                                                              'roll_no': 'r', 'branch': 'CSE', 'cgpa': 11, 'phone': '12'})
        self.assertEqual(bad.status_code, 400)
        for f in ('email', 'password', 'cgpa', 'phone'):
            self.assertIn(f, bad.data)

    def test_duplicate_email_rejected(self):
        self.register_student()
        self.assertEqual(self.register_student(roll='R9').status_code, 400)

    def test_role_based_access(self):
        self.approved_student()
        self.login('s1@x.edu')
        self.assertEqual(self.client.get('/api/admin/users/').status_code, 403)
        self.assertEqual(self.client.get('/api/companies/').status_code, 403)
        self.assertEqual(self.client.post('/api/reports/', {}).status_code, 403)
        self.logout_client()
        self.assertEqual(self.client.get('/api/jobs/').status_code, 401)

    def test_profile_update_whitelist(self):
        self.approved_student()
        self.login('s1@x.edu')
        r = self.client.put('/api/auth/profile/', {'cgpa': 9.1, 'roll_no': 'HACK', 'email': 'h@x.edu'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['cgpa'], 9.1)
        self.assertEqual(r.data['roll_no'], 'R1')
        self.assertEqual(r.data['email'], 's1@x.edu')

    # ---- full placement flow ----
    def test_full_flow(self):
        self.approved_student()
        self.approved_student(email='s2@x.edu', roll='R2', cgpa=5.0, branch='ME')
        self.approved_officer()
        self.login('po@x.edu')
        company = self.client.post('/api/companies/', {'name': 'Acme', 'hr_email': 'hr@acme.com'}, format='json')
        self.assertEqual(company.status_code, 201, company.data)
        job_data = {'company': company.data['id'], 'title': 'SDE', 'description': 'Build', 'package': '8 LPA',
                    'min_cgpa': 7, 'allowed_branches': 'CSE, IT',
                    'last_date': str(timezone.localdate() + timedelta(days=5))}
        past = dict(job_data, last_date=str(timezone.localdate() - timedelta(days=1)))
        self.assertEqual(self.client.post('/api/jobs/', past, format='json').status_code, 400)
        job = self.client.post('/api/jobs/', job_data, format='json')
        self.assertEqual(job.status_code, 201, job.data)
        job_id = job.data['id']
        # only the eligible student (s1) is notified
        self.assertEqual(Notification.objects.filter(user__email='s1@x.edu', message__startswith='New job').count(), 1)
        self.assertEqual(Notification.objects.filter(user__email='s2@x.edu', message__startswith='New job').count(), 0)

        # ineligible student sees no jobs
        self.login('s2@x.edu')
        self.assertEqual(len(self.client.get('/api/jobs/').data), 0)
        self.assertEqual(self.client.post(f'/api/jobs/{job_id}/apply/').status_code, 404)

        # eligible student applies once
        self.login('s1@x.edu')
        self.assertEqual(len(self.client.get('/api/jobs/').data), 1)
        r = self.client.post(f'/api/jobs/{job_id}/apply/')
        self.assertEqual(r.status_code, 201, r.data)
        app_id = r.data['id']
        self.assertEqual(self.client.post(f'/api/jobs/{job_id}/apply/').status_code, 400)
        self.assertTrue(self.client.get('/api/jobs/').data[0]['has_applied'])
        # student cannot change status
        self.assertEqual(self.client.patch(f'/api/applications/{app_id}/status/', {'status': 'placed'}).status_code, 403)

        # officer: invalid jump applied->placed refused, then shortlist, drive, place
        self.login('po@x.edu')
        self.assertEqual(self.client.patch(f'/api/applications/{app_id}/status/', {'status': 'placed'}).status_code, 400)
        self.assertEqual(self.client.patch(f'/api/applications/{app_id}/status/', {'status': 'shortlisted'}).status_code, 200)
        drive = self.client.post('/api/drives/', {'job': job_id, 'drive_date': str(timezone.localdate() + timedelta(days=7)),
                                                  'venue': 'Seminar Hall'}, format='json')
        self.assertEqual(drive.status_code, 201, drive.data)
        self.assertEqual(self.client.patch(f'/api/applications/{app_id}/status/', {'status': 'placed'}).status_code, 200)
        placed = self.client.get('/api/placed-students/').data
        self.assertEqual(len(placed), 1)
        self.assertEqual(placed[0]['result']['status'], 'selected')
        self.assertEqual(self.client.get('/api/dashboard/').data['placed'], 1)

        # student sees status, drive, notifications
        self.login('s1@x.edu')
        self.assertEqual(self.client.get('/api/applications/').data[0]['status'], 'placed')
        self.assertEqual(len(self.client.get('/api/drives/').data), 1)
        notes = self.client.get('/api/notifications/').data
        self.assertGreaterEqual(len(notes), 4)
        self.assertEqual(self.client.post('/api/notifications/read-all/').status_code, 204)
        self.assertEqual(self.client.get('/api/dashboard/').data['unread_notifications'], 0)

        # admin report + activity log
        self.login('admin@x.edu')
        rep = self.client.post('/api/reports/', {'report_type': 'summary'}, format='json')
        self.assertEqual(rep.status_code, 201)
        self.assertEqual(rep.data['data']['placed_students'], 1)
        self.assertEqual(rep.data['data']['total_students'], 2)
        for t in ('company_wise', 'branch_wise'):
            self.assertEqual(self.client.post('/api/reports/', {'report_type': t}, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/reports/', {'report_type': 'zzz'}, format='json').status_code, 400)
        self.assertGreater(len(self.client.get('/api/admin/activity/').data), 5)
        self.assertEqual(self.client.get('/api/dashboard/').data['students'], 2)

    def test_rejected_user_cannot_login(self):
        self.register_student()
        User.objects.get(email='s1@x.edu').reject()
        r = self.client.post('/api/auth/login/', {'email': 's1@x.edu', 'password': PWD})
        self.assertEqual(r.data['code'], 'rejected')

    # ---- resume ----
    def test_resume_upload_rules_and_privacy(self):
        self.approved_student(resume=False)
        self.approved_student(resume=False, email='s2@x.edu', roll='R2')
        self.approved_officer()
        self.login('s1@x.edu')
        up = lambda name, data: self.client.post('/api/auth/resume/', {'resume': SimpleUploadedFile(name, data)}, format='multipart')
        self.assertEqual(up('cv.txt', PDF).status_code, 400)
        self.assertEqual(up('cv.pdf', b'not a pdf').status_code, 400)
        self.assertEqual(up('cv.pdf', b'%PDF-' + b'0' * (3 * 1024 * 1024)).status_code, 400)
        r = up('cv.pdf', PDF)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data['has_resume'])
        me = User.objects.get(email='s1@x.edu').pk
        other = User.objects.get(email='s2@x.edu').pk
        self.assertEqual(self.client.get(f'/api/students/{me}/resume/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/students/{other}/resume/').status_code, 403)  # not someone else's
        self.login('po@x.edu')
        self.assertEqual(self.client.get(f'/api/students/{me}/resume/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/students/{other}/resume/').status_code, 404)  # none uploaded
        self.login('s1@x.edu')
        self.assertFalse(self.client.delete('/api/auth/resume/').data['has_resume'])

    def test_cannot_apply_without_resume(self):
        self.approved_student(resume=False)
        self.approved_officer()
        self.login('po@x.edu')
        c = self.client.post('/api/companies/', {'name': 'Acme', 'hr_email': 'hr@acme.com'}, format='json').data['id']
        j = self.client.post('/api/jobs/', {'company': c, 'title': 'SDE', 'description': 'x', 'package': '5 LPA',
                                            'last_date': str(timezone.localdate() + timedelta(days=3))}, format='json').data['id']
        self.login('s1@x.edu')
        r = self.client.post(f'/api/jobs/{j}/apply/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('resume', str(r.data).lower())

    # ---- verification ----
    def test_admin_verification_review_and_reject_reason(self):
        self.register_student()
        self.login('admin@x.edu')
        uid = self.client.get('/api/admin/users/?status=pending').data[0]['id']
        detail = self.client.get(f'/api/admin/users/{uid}/').data
        self.assertEqual(detail['profile']['roll_no'], 'R1')
        self.assertEqual(self.client.post(f'/api/admin/users/{uid}/reject/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/api/admin/users/{uid}/reject/', {'reason': 'Roll number not found'}, format='json').status_code, 200)
        self.logout_client()
        r = self.client.post('/api/auth/login/', {'email': 's1@x.edu', 'password': PWD})
        self.assertIn('Roll number not found', r.data['detail'])
        self.login('admin@x.edu')
        self.client.post(f'/api/admin/users/{uid}/approve/')
        u = User.objects.get(pk=uid)
        self.assertEqual(u.status, 'approved')
        self.assertEqual(u.verified_by_id, self.admin.pk)
        self.assertEqual(u.rejection_reason, '')

    # ---- admin assigns tasks to officers ----
    def test_admin_assigns_task_officer_updates(self):
        po = self.approved_officer()
        self.approved_student()
        self.login('admin@x.edu')
        data = {'title': 'Shortlist CSE students', 'task_type': 'shortlist', 'assigned_to': po.pk, 'priority': 'high',
                'due_date': str(timezone.localdate() + timedelta(days=2))}
        r = self.client.post('/api/tasks/', data, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        tid = r.data['id']
        self.assertEqual(r.data['assigned_to_name'], 'PO')
        past = dict(data, due_date=str(timezone.localdate() - timedelta(days=1)))
        self.assertEqual(self.client.post('/api/tasks/', past, format='json').status_code, 400)
        stu = Student.objects.first()
        self.assertEqual(self.client.post('/api/tasks/', dict(data, assigned_to=stu.pk), format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/dashboard/').data['open_tasks'], 1)
        # officer sees only own task, is notified, and reports progress
        self.login('po@x.edu')
        self.assertEqual(len(self.client.get('/api/tasks/').data), 1)
        self.assertEqual(Notification.objects.filter(user=po, message__startswith='New task').count(), 1)
        self.assertEqual(self.client.post('/api/tasks/', data, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/tasks/{tid}/').status_code, 403)
        self.assertEqual(self.client.post(f'/api/tasks/{tid}/progress/', {'status': 'in_progress'}, format='json').status_code, 200)
        done = self.client.post(f'/api/tasks/{tid}/progress/', {'status': 'completed', 'officer_note': 'Done, 12 shortlisted'}, format='json')
        self.assertEqual(done.data['status'], 'completed')
        self.assertEqual(self.client.post(f'/api/tasks/{tid}/progress/', {'status': 'pending'}, format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/dashboard/').data['open_tasks'], 0)
        # admin was notified
        self.assertEqual(Notification.objects.filter(user=self.admin, message__contains='marked').count(), 2)
        # students cannot see tasks
        self.login('s1@x.edu')
        self.assertEqual(self.client.get('/api/tasks/').status_code, 403)


class OopTests(APITestCase):
    def test_inheritance_and_polymorphism(self):
        s = Student.register(PWD, name='A', email='a@x.edu', roll_no='1', branch='CSE', cgpa=8, phone='1234567890')
        self.assertIsInstance(s, User)
        self.assertIs(type(User.objects.get(pk=s.pk).get_profile()), Student)
        self.assertIn('applications_total', s.get_dashboard_summary())
        a = Admin.register(PWD, name='B', email='b@x.edu')
        self.assertIn('pending_users', a.get_dashboard_summary())
