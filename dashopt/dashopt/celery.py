from celery import Celery
from django.conf import settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashopt.settings')

app = Celery("dashopt", broker='redis://@127.0.0.1:6379/2')

app.autodiscover_tasks(settings.INSTALLED_APPS)
