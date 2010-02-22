#!/bin/bash

PYTHON25=/usr/bin/python2.5
PYTHON26=/usr/bin/python2.6

USERNAME=cnshot
PASSWORD=password

LTS_DIR=`dirname $0`
export PATH=$PATH:${LTS_DIR}
export DJANGO_SETTINGS_MODULE=settings
export PYTHONPATH=${LTS_DIR}/lts_web

nohup ${LTS_DIR}/failover.sh ${PYTHON25} ${LTS_DIR}/shot_service.py -n 8 -t 30 \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
nohup ${LTS_DIR}/failover.sh ${PYTHON25} ${LTS_DIR}/rt_shot.py -u ${USERNAME} -p ${PASSWORD} \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
nohup ${LTS_DIR}/failover.sh task_gc.py &
nohup ${LTS_DIR}/failover.sh ${PYTHON25} ${LTS_DIR}/url_processor.py \
    -p ${LTS_DIR}/link_tweet_shot.sqlite \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
