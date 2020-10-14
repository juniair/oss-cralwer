# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import Celery
from kombu import Queue

# app = Celery('crawler', broker='amqp://admin:12345678@rabbit:5672', backend='rpc://', include=['crawler.project_tasks', 'crawler.download_tasks'])
app = Celery(
    'crawler', 
    broker='amqp://admin:12345678@localhost:5672', 
    backend='rpc://', 
    include=['sourceforge.project_page', 'sourceforge.source_page', 'github.project_page', 'github.source_page']
    )

app.conf.task_default_queue = 'project_queue'

# to use multiple queues
app.conf.task_queues = (
    Queue('project_queue', routing_key='project_task'),
    Queue('source_queue', routing_key='source_task')
    )
app.conf.task_routes = {
    "sourceforge.project_page.get_project_info_from_sourceforge":{"queue":"project_queue", "routing_key":"project_task"}, 
    "sourceforge.source_page.download_from_sourceforge_code_tab":{"queue":"source_queue", "routing_key":"source_task"},
    "sourceforge.source_page.download_from_sourceforge_files_tab":{"queue":"source_queue", "routing_key":"source_task"},
    "github.project_page.get_release_info":{"queue":"project_queue", "routing_key":"source_task"},
    "github.source_page.get_source_code":{"queue":"source_queue", "routing_key":"source_task"},
    }


if __name__ == '__main__':
    app.start()