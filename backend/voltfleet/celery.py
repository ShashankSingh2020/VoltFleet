import os
from celery import Celery

# Set default Django settings module for Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voltfleet.settings")

app = Celery("voltfleet")

# Read Celery configurations prefixed with CELERY_ from settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")