#!/usr/bin/python

import stompy, os

class GCWorker:
    def __init__(self, id='UNKNOWN'):
        self.id = id

    def run(self):
        pid = os.fork()
        if pid > 0:
            return pid

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
