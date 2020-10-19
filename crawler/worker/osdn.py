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
    include=['osdn.project_page', 'osdn.source_page']
    )

app.conf.task_default_queue = 'osdn_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('osdn_project_queue', routing_key='osdn_project_task'),
    Queue('osdn_source_queue', routing_key='osdn_source_task')
    )
app.conf.task_routes = {
    "osdn.project_page.get_project_info":{"queue":"osdn_project_queue", "routing_key":"osdn_project_task"},
    "osdn.source_page.get_source_code":{"queue":"osdn_source_queue", "routing_key":"osdn_source_task"},
    }


if __name__ == '__main__':
    app.start()