# opensource-crawler

# 가상환경 생성 : virtualenv 
- 가상환경 생성
$virtualenv -p python3 ./venv
- 가상환경 실행
$source ./venv/bin/activate
- 가상환경 종료
$deactivate

# 모듈 import 시 주의
- crawler 아래에 존재 하기 때문에 모듈 위치를 지정해야 한다.
(수정 예)  
from sourceforge import SourceForgeCrawler  
from celery import app  
from GetRepoInfo import *  
import VCSDownloader, md5hasher  

### 실행 : 
$celery --app=worker.app worker --loglevel=debug -Q project_queue -c 2 --hostname=<식별자>@%h --logfile=./celery.log
$celery --app=worker.app worker --loglevel=debug -Q source_queue -c 4 --hostname=<식별자>@%h --logfile=./celery.log
$celery multi start worker --app=worker.app -l debug --hostname=<식별자>@%h
$celery multi stop worker
- pidfile 지정, logfile 지정
$ celery multi start w1 -A proj -l info --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log

ex) 
$celery --app=worker.app worker -l debug -Q project_queue --hostname=sourceforge.project@%h --logfile=./celery.log
$celery --app=worker.app worker -l debug -Q source_queue --hostname=sourceforge.source@%h --logfile=./celery.log


### Broker : rabbitmq
$docker run -it --rm --name rabbit -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=12345678 rabbitmq:latest

이미지 : rabbitmq:latest or rabbitmq:3-management


### PostgreSQL
$docker run -it --rm [-d] -p 15432:5432 --name pgsql -e POSTGRES_PASSWORD=12345678 -v [/data]:/var/lib/postgresql/data postgres

### scale up number of workers
$docker-compose scale worker=5
$docker-compose up -d --scale worker=2

## 실행
$docker-compose up -d
$docker-compose exec <main worker name> python [시작 python] [파라미터...]


## Tor 
Tor is free software and an open network that helps you defend against traffic analysis, a form of network surveillance that threatens personal freedom and privacy, confidential business activities and relationships, and state security.  
- https://github.com/dperson/torproxy
- Docker image
$sudo docker run -it -p 8118:8118 -p 9050:9050 -d dperson/torproxy
 - webproxy : 8118 (http://host-ip:8118)
 - socks proxy : 9050 (socks5://host-ip:9050)



# uhura server
- mq
$ sudo docker run -it --rm --name rabbit -p 5672:5672 -p 15672:15672 -d -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=12345678 -v /HDD2/opensource_crawler/mq/data:/var/lib/rabbitmq/mnesia/ rabbitmq:latest
- postgresql
$ sudo docker run -it --rm -p 15432:5432 --name pgsql -e POSTGRES_PASSWORD=12345678 -v /HDD2/opensource_crawler/postgres/data:/var/lib/postgresql/data postgres
- tor network
$ sudo docker run -it -p 8118:8118 -p 9050:9050 -d dperson/torproxy

