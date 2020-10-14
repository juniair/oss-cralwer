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
    include=['launchpad.project_page', 'launchpad.source_page']
    )

app.conf.task_default_queue = 'launchpad_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('launchpad_project_queue', routing_key='launchpad_project_task'),
    Queue('launchpad_source_queue', routing_key='launchpad_source_task')
    )
app.conf.task_routes = {
    "launchpad.project_page.get_project_info":{"queue":"launchpad_project_queue", "routing_key":"launchpad_project_task"},
    "launchpad.source_page.get_source_code":{"queue":"launchpad_source_queue", "routing_key":"launchpad_source_task"},
    }


if __name__ == '__main__':
    app.start()