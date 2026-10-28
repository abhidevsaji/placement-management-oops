from django.core.management.base import BaseCommand

from accounts.models import Admin


class Command(BaseCommand):
    help = 'Create an approved Admin account: python manage.py create_admin you@college.edu "Your Name" password'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('name')
        parser.add_argument('password')

    def handle(self, *args, **o):
        user = Admin.register(o['password'], name=o['name'], email=o['email'])
        user.approve()
        self.stdout.write(self.style.SUCCESS(f'Admin created: {user.email}'))
