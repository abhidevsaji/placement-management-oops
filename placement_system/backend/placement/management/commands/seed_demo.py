"""Creates demo accounts + data so you can try the app quickly:  python manage.py seed_demo"""
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Admin, PlacementOfficer, Student
from placement.models import Application, Company, JobPosting, Task

SAMPLE_PDF = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF'

PWD = 'Demo@12345'


class Command(BaseCommand):
    help = 'Load demo users, companies and jobs'

    def handle(self, *args, **opts):
        if Admin.objects.filter(email='admin@college.edu').exists():
            self.stdout.write('Demo data already loaded.')
            return
        admin = Admin.register(PWD, name='Demo Admin', email='admin@college.edu'); admin.approve()
        po = PlacementOfficer.register(PWD, name='Demo Officer', email='officer@college.edu',
                                       department='Training & Placement Cell', phone='9876500001'); po.approve()
        students = []
        for i, (name, branch, cgpa) in enumerate([('Anu Menon', 'CSE', 8.6), ('Rahul Nair', 'ECE', 7.4), ('Sneha Das', 'CSE', 6.2)], 1):
            s = Student.register(PWD, name=name, email=f'student{i}@college.edu', roll_no=f'CS26{i:03}',
                                 branch=branch, cgpa=cgpa, phone=f'98765000{i:02}', address='Thrissur, Kerala')
            s.approve(); students.append(s)
            s.attach_resume(ContentFile(SAMPLE_PDF, name='resume.pdf'))
        Student.register(PWD, name='Pending Student', email='pending@college.edu', roll_no='CS26099',
                         branch='IT', cgpa=7.9, phone='9876500099')   # waits for admin approval
        tcs = Company.objects.create(name='TechNova Solutions', hr_email='hr@technova.com', phone='0487000111',
                                     address='Kochi', description='Software services company.', created_by=po)
        mech = Company.objects.create(name='Gearworks Ltd', hr_email='jobs@gearworks.com', created_by=po)
        due = timezone.localdate() + timedelta(days=14)
        j1 = JobPosting.objects.create(company=tcs, title='Software Engineer', description='Backend and web development.',
                                       package='6.5 LPA', min_cgpa=7, allowed_branches='CSE, IT, ECE',
                                       eligibility_criteria='CGPA 7.0+, no active backlogs', last_date=due, posted_by=po)
        JobPosting.objects.create(company=mech, title='Graduate Engineer Trainee', description='Plant operations.',
                                  package='4 LPA', min_cgpa=6, allowed_branches='ME, EEE', last_date=due, posted_by=po)
        Application.apply(students[0], j1)
        Task.assign(admin, assigned_to=po, title='Shortlist students for Software Engineer', task_type='shortlist',
                    priority='high', due_date=timezone.localdate() + timedelta(days=3))
        self.stdout.write(self.style.SUCCESS(f'Demo data ready. All demo passwords: {PWD}'))
