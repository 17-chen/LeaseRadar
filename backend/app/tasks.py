import os
from celery import Celery
from sqlalchemy import select
from .db import Session, Source
from .service import crawl, deliver_local, poll_jobs

celery = Celery('leaseradar', broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
celery.conf.update(timezone='Asia/Shanghai', task_acks_late=True, worker_prefetch_multiplier=1,
    beat_schedule={'check-sources': {'task': 'app.tasks.schedule', 'schedule': 15},
                   'deliver-inbox': {'task': 'app.tasks.deliver', 'schedule': 15}})

@celery.task
def collect(source_id):
    return crawl(source_id)

@celery.task
def schedule():
    poll_jobs()

@celery.task
def deliver():
    deliver_local()
