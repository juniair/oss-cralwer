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
    include=['sourceforge.project_page', 'sourceforge.source_page']
    )

app.conf.task_default_queue = 'sf_project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('sf_project_queue', routing_key='sf_project_task'),
    Queue('sf_source_queue', routing_key='sf_source_task')
    )
app.conf.task_routes = {
    "sourceforge.project_page.get_project_info_from_sourceforge":{"queue":"sf_project_queue", "routing_key":"sf_project_task"}, 
    "sourceforge.source_page.download_from_sourceforge_code_tab":{"queue":"sf_source_queue", "routing_key":"sf_source_task"},
    "sourceforge.source_page.download_from_sourceforge_files_tab":{"queue":"sf_source_queue", "routing_key":"sf_source_task"},
    }


if __name__ == '__main__':
    app.start()