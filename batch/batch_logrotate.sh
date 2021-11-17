#!/bin/bash

BASE_DAY="$(date -d yesterday +%Y-%m-%d)"

cd /app/log/batch
tar zcvf batch.$BASE_DAY.log.tar.gz ./batch.log ./batch_error.log
cat /dev/null > ./batch.log
cat /dev/null > ./batch_error.log

cd /app/log/clare
tar zcvf clare_add.$BASE_DAY.log.tar.gz ./clare_add.log
cat /dev/null > ./clare_add.log

tar zcvf clare_index.$BASE_DAY.log.tar.gz ./clare_index.log
cat /dev/null > ./clare_index.log
