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
    include=['ow2.project_page', 'ow2.source_page']
    )

app.conf.task_default_queue = 'ow2_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('ow2_project_queue', routing_key='ow2_project_task'),
    Queue('ow2_source_queue', routing_key='ow2_source_task')
    )
app.conf.task_routes = {
    "ow2.project_page.get_project_info":{"queue":"ow2_project_queue", "routing_key":"ow2_project_task"},
    "ow2.source_page.get_source_code":{"queue":"ow2_source_queue", "routing_key":"ow2_source_task"},
    }


if __name__ == '__main__':
    app.start()