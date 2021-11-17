#!/bin/bash
BASE_DAY="$(date -d yesterday +%Y-%m-%d)"

cd /app/log/crawler
tar zcvf crawler.$BASE_DAY.log.tar.gz /app/log/main_github.log 
cat /dev/null > /app/log/main_github.log 

cd /app/log/github
tar zcvf worker.github.$BASE_DAY.log.tar.gz /app/log/worker.github.project.log /app/log/worker.github.source.log
cat /dev/null > /app/log/worker.github.project.log
cat /dev/null > /app/log/worker.github.source.log
