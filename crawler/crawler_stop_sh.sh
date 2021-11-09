#!/bin/bash
target=$1

if [ $# -eq 2 ] ; then
    target2=$2
else
    target2=$1
fi


export CELERY_APP=worker.${target}.app

echo stopping $CELERY_APP





# echo ""

echo stop ${target2}_project_queue

celery multi stop worker.${target} --app=worker.${target}.app -l debug -Q ${target2}_source_queue --hostname=${target}.source@%h --pidfile=/app/run/${target}/worker.${target}.source.pid


echo stop ${target2}_project_queue

celery multi stop worker.${target} --app=worker.${target}.app -l debug -Q ${target2}_project_queue --hostname=${target}.project@%h


PID=`ps -eaf | grep main_${target}.py | grep -v grep | awk '{print $2}'` 
if [[ "" != "$PID" ]]; then 
    echo background stop main_${target}.py
    kill -TERM $PID 
else
    echo main_${target}.py is not background running.
fi

echo $CELERY_APP stoped.

#celery multi start worker.${target} -l debug -Q ${target}_indexing_queue --hostname=${target}.indexing@%h --logfile=/var/log/celery/worker.${target}.indexing.log --autoscale=8,3 --pidfile=/var/run/celery/worker.${target}.indexing.pid
# celery 모니터링 툴(web) 별도로 실행
# nohup flower -A worker.${target}.app --port=5555 2>&1 >> /var/log/celery/flower_worker.${target}.log &