#!/bin/bash
target=$1
if [ $# -eq 2 ] ; then
    target2=$2
else
    target2=$1
fi

export CELERY_APP=worker.${target}.app


echo $CELERY_APP
echo start ${target2}_project_queue

# celery multi start worker.${target} --app=worker.${target}.app -l debug -Q ${target2}_project_queue -c 3 --hostname=${target}.project@%h --logfile=/app/log/${target}/worker.${target}.project.log
celery multi start worker.${target} --app=worker.${target}.app -l debug -Q ${target2}_project_queue -c 3 --hostname=${target}.project@%h --logfile=/app/log/${target}/worker.${target}.project.log --pidfile=/app/run/${target}/worker.${target}.project.pid


echo start ${target2}_source_queue

celery multi start worker.${target} --app=worker.${target}.app -l debug -Q ${target2}_source_queue --autoscale=10,3 --hostname=${target}.source@%h --logfile=/app/log/${target}/worker.${target}.source.log --pidfile=/app/run/${target}/worker.${target}.source.pid

PID=`ps -eaf | grep main_${target}.py | grep -v grep` 
if [[ "" != "$PID" ]]; then 
    echo main_${target}.py is background started.
else
    echo background start main_${target}.py
    nohup python3 ./main_${target}.py > ./log/crawler/main_${target}.log 2>&1 &
fi


echo ${CELERY_APP} running

#celery multi start worker.${target} -l debug -Q ${target}_indexing_queue --hostname=${target}.indexing@%h --logfile=/var/log/celery/worker.${target}.indexing.log --autoscale=8,3 --pidfile=/var/run/celery/worker.${target}.indexing.pid
# celery 모니터링 툴(web) 별도로 실행
# nohup flower -A worker.${target}.app --port=5555 2>&1 >> /var/log/celery/flower_worker.${target}.log &
