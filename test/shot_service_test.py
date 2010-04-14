#!/usr/bin/python

import sys, os
import signal, time, logging, logging.config, threading, stompy, pickle
import unittest
import Queue

from PyQt4.QtCore import *
from PyQt4.QtGui import *

d = os.path.dirname(__file__)
if d == '':
   d = '.' 
sys.path.append(d + '/../')
    
import shot_service

class DummyOptions(object):
    pass

class ScreenshotWorkerTest(unittest.TestCase):
    def setUp(self):
        self.options = DummyOptions()

        self.options.max_width=640
        self.options.max_height=480
        self.options.source_queue="/queue/shot_serivce_test"
        self.options.dest_queue="/queue/shot_dest_test"
        self.options.cancel_queue="/queue/cancel_test"
        self.options.timeout = 20

        logging.basicConfig(level=logging.DEBUG)

        self.app = QApplication([])
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        
    def tearDown(self):
        pass

    def test_shot(self):
        # enqueue task
        stomp = stompy.simple.Client()
        stomp.connect()

        stomp.put(pickle.dumps({'url':'http://g.cn/', 'filename':None}),
                  destination=self.options.source_queue)

        stomp.disconnect()

        # start worker
        shot_service.logger = logging
        shot_service.options = self.options
        t = shot_service.ScreenshotWorker()

        t.start()
        t.postSetup('1')

        threading.Timer(5, self.end_test_shot).start()

        self.app.exec_()

    def end_test_shot(self):
        self.app.exit()
        
        stomp = stompy.simple.Client()
        stomp.connect()

        try:
            stomp.subscribe(self.options.dest_queue)
            try:
                m=stomp.get_nowait()
                self.assert_(m is not None)
            except stompy.simple.Client.Empty:
                self.fail
            stomp.unsubscribe(self.options.dest_queue)

            stomp.subscribe(self.options.cancel_queue)
            try:
                m = stomp.get_nowait()
                self.fail("Got a canceld task..")
            except stompy.simple.Client.Empty:
                pass
            stomp.unsubscribe(self.options.cancel_queue)
        finally:
            stomp.disconnect()

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ScreenshotWorkerTest)
    unittest.TextTestRunner(verbosity=1).run(suite)

