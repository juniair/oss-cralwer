# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import Celery
from kombu import Queue

from common import getenv

CELERY_BROKER = getenv("CELERY_BROKER", 'amqp://admin:12345678@localhost:5672', True)

app = Celery(
    'crawler', 
    broker=CELERY_BROKER, 
    backend='rpc://', 
    include=['bitbucket.project_page', 'bitbucket.source_page']
    )

app.conf.task_default_queue = 'bitbucket_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('bitbucket_project_queue', routing_key='bitbucket_project_task'),
    Queue('bitbucket_source_queue', routing_key='bitbucket_source_task')
    )
app.conf.task_routes = {
    "bitbucket.project_page.get_release_info":{"queue":"bitbucket_project_queue", "routing_key":"bitbucket_project_task"},
    "bitbucket.source_page.get_source_code":{"queue":"bitbucket_source_queue", "routing_key":"bitbucket_source_task"},
    }


if __name__ == '__main__':
    app.start()