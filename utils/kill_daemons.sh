#!/bin/sh

for D in url_processor.py shot_service.py rt_shot.py task_gc.py; do
	echo $D
	./kill_failover.sh $D
done
