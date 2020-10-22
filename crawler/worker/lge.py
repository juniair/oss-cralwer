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
    include=['LGE.LGEcrawler']
    )

app.conf.task_default_queue = 'lge_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('lge_project_queue', routing_key='lge_project_task')
    )

app.conf.task_routes = {
    "sourceforge.project_page.get_project_info_from_sourceforge":{"queue":"lge_project_queue", "routing_key":"lge_project_task"}
    }

if __name__ == '__main__':
    app.start()