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
    include=['eclipse.project_page', 'eclipse.source_page']
    )

app.conf.task_default_queue = 'eclipse_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('eclipse_project_queue', routing_key='eclipse_project_task'),
    Queue('eclipse_source_queue', routing_key='eclipse_source_task')
    )
app.conf.task_routes = {
    "eclipse.project_page.get_project_info":{"queue":"eclipse_project_queue", "routing_key":"eclipse_project_task"},
    "eclipse.source_page.get_source_code":{"queue":"eclipse_source_queue", "routing_key":"eclipse_source_task"},
    }


if __name__ == '__main__':
    app.start()