#!/usr/bin/python

import stompy

from lts.process_manager import ProcessWorker

class GCWorker(ProcessWorker):
    def run(self):
        stomp = stompy.simple.Client()
        stomp.connect()
        stomp.subscribe("/queue/cancel", ack='auto')
        while True:
            m=stomp.get()

if __name__ == '__main__':
    stomp = stompy.simple.Client()
    stomp.connect()
    stomp.subscribe("/queue/cancel", ack='auto')
    while True:
        m=stomp.get()
