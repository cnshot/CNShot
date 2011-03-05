#!/bin/sh

LTS_DIR=`dirname $0`
export PATH=$PATH:${LTS_DIR}

nohup ${LTS_DIR}/failover.sh startx -- \
    `which Xvfb` :1 -screen 0 1024x768x24 &