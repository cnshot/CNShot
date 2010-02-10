#!/bin/bash

PYTHON25=/usr/bin/python2.5
PYTHON26=/usr/bin/python2.6

USERNAME=pageshot
PASSWORD=password

LTS_DIR=`basename $0`
export PATH=$PATH:${LTS_DIR}

nohup failover.sh ${PYTHON25} ${LTS_DIR}/shot_service.py -n 20 -t 30 \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
nohup failover.sh ${PYTHON25} ${LTS_DIR}/rt_shot.py -u ${USERNAME} -p ${PASSWORD} \
    -l ${LTS_DIR}/link_shot_tweet_log.conf -d -k &
nohup failover.sh task_gc.py &
nohup failover.sh ${PYTHON25} ${LTS_DIR}/url_processor.py \
    -p ${LTS_DIR}/link_tweet_shot.sqlite \
    -l ${LTS_DIR}/link_shot_tweet_log.conf &
