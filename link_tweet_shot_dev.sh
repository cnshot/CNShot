#!/bin/bash

PYTHON25=/usr/bin/python2.5
PYTHON26=/usr/bin/python2.6

USERNAME=shotdev
PASSWORD=password

LTS_DIR=`dirname $0`
export PATH=$PATH:${LTS_DIR}
export DJANGO_SETTINGS_MODULE=settings
export PYTHONPATH=${LTS_DIR}/lts_web

nohup tsocks ${LTS_DIR}/failover.sh ${LTS_DIR}/shot_service.py -n 4 -t 30 \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
nohup tsocks ${LTS_DIR}/failover.sh ${LTS_DIR}/rt_shot.py -u ${USERNAME} -p ${PASSWORD} \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
nohup ${LTS_DIR}/failover.sh task_gc.py &
nohup tsocks ${LTS_DIR}/failover.sh ${LTS_DIR}/url_processor.py \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
