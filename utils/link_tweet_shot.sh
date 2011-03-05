#!/bin/bash

PYTHON25=/usr/bin/python2.5
PYTHON26=/usr/bin/python2.6

LTS_DIR=`dirname $0`
export PATH=$PATH:${LTS_DIR}
export DJANGO_SETTINGS_MODULE=settings
export PYTHONPATH=${LTS_DIR}/lts_web

nohup ${LTS_DIR}/failover.sh ${LTS_DIR}/shot_service.py &
nohup ${LTS_DIR}/failover.sh ${LTS_DIR}/rt_shot.py &
nohup ${LTS_DIR}/failover.sh task_gc.py &
nohup ${LTS_DIR}/failover.sh ${LTS_DIR}/url_processor.py &
