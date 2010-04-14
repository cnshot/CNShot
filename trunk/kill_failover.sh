#!/bin/sh

EXEC=`basename $1`

PID_DIR=/tmp
PID_POSTFIX=".pid"
PID_FILE="${PID_DIR}/${EXEC}${PID_POSTFIX}"

if [ ! -f "${PID_FILE}" ]; then
    echo "No pid file named ${PID_FILE} is found!" >/dev/stderr
    exit 1
fi

EXEC_PID=`cat ${PID_FILE}`
echo "Killing ${EXEC} process ${EXEC_PID} ..."
kill "${EXEC_PID}"
