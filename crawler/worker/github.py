# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import Celery
from kombu import Queue

from common import getenv

CELERY_BROKER = getenv("CELERY_BROKER", 'amqp://admin:12345678@localhost:5672', True)
# app = Celery('crawler', broker='amqp://admin:12345678@rabbit:5672', backend='rpc://', include=['crawler.project_tasks', 'crawler.download_tasks'])
app = Celery(
    'crawler', 
    broker=CELERY_BROKER, 
    backend='rpc://', 
    include=['github.project_page', 'github.source_page']
    )

app.conf.task_default_queue = 'git_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('git_project_queue', routing_key='git_project_task'),
    Queue('git_source_queue', routing_key='git_source_task')
    )
app.conf.task_routes = {
    "github.project_page.get_release_info":{"queue":"git_project_queue", "routing_key":"git_project_task"},
    "github.source_page.get_source_code":{"queue":"git_source_queue", "routing_key":"git_source_task"},
    }


if __name__ == '__main__':
    app.start()