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
    include=['gitlab.project_page', 'gitlab.source_page']
    )

app.conf.task_default_queue = 'gitlab_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('gitlab_project_queue', routing_key='gitlab_project_task'),
    Queue('gitlab_source_queue', routing_key='gitlab_source_task')
    )
app.conf.task_routes = {
    "gitlab.project_page.get_project_info":{"queue":"gitlab_project_queue", "routing_key":"gitlab_project_task"},
    "gitlab.source_page.get_source_code":{"queue":"gitlab_source_queue", "routing_key":"gitlab_source_task"},
    }


if __name__ == '__main__':
    app.start()