#!/bin/bash

CMD_LINE=$@
EXEC=${EXEC:=`basename $1`}

PID_DIR=/tmp
PID_POSTFIX=".pid"
PID_FILE="${PID_DIR}/${EXEC}${PID_POSTFIX}"

restart(){
    echo "Restarting child ..."

    set -bm
    trap restart SIGCHLD

    $CMD_LINE &
    CHILD_PID=$!
    echo $CHILD_PID
}

stop_all(){
    echo "Stop child ..."

    set -bm
    trap '' SIGCHLD

    kill $CHILD_PID

    rm "${PID_FILE}"
    exit 0
}

if [ -f "${PID_FILE}" ]; then
    ps -p `cat ${PID_FILE}` >/dev/null && \
	echo "${EXEC} is running!" >/dev/stderr && \
	exit 1
    rm "${PID_FILE}"
fi

echo $$ >"${PID_FILE}"

trap stop_all SIGTERM SIGINT

restart

wait
