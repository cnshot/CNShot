#!/usr/bin/python

import stompy

if __name__ == '__main__':
    stomp = stompy.simple.Client()
    stomp.connect()
    stomp.subscribe("/queue/cancel", ack='auto')
    while True:
        m=stomp.get()
