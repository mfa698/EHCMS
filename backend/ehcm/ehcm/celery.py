import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ehcm.settings")

app = Celery("ehcm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "daily-contract-expiry-check": {
        "task": "contracts.tasks.check_contract_expiries",
        "schedule": crontab(hour=7, minute=0),
    },
}
