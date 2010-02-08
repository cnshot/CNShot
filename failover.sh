#!/bin/bash

CMD_LINE=$@

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

    exit 0
}

trap stop_all SIGTERM SIGINT

restart

wait
