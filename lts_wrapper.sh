#!/bin/bash

CMD_LINE=$@

LTS_DIR=`dirname $0`
export PATH=$PATH:${LTS_DIR}
export DJANGO_SETTINGS_MODULE=settings
export PYTHONPATH=${LTS_DIR}/lts_web

${CMD_LINE}