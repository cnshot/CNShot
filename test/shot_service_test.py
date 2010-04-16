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

        self.options.queues = DummyOptions()
        self.options.queues.processed = "/queue/shot_serivce_test"
        self.options.queues.shotted ="/queue/shot_dest_test"
        self.options.queues.cancel = "/queue/cancel_test"

        self.options.shot_service = DummyOptions()
        self.options.shot_service.max_width = 1024
        self.options.shot_service.max_height = 768
        self.options.shot_service.timeout = 20

        logging.basicConfig(level=logging.DEBUG)

        self.app = QApplication([])
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        self.pool_sema = threading.Semaphore(value=1)
        
    def tearDown(self):
        pass

    def test_shot(self):
        self.pool_sema.acquire()

        # enqueue task
        stomp = stompy.simple.Client()
        stomp.connect()

        stomp.put(pickle.dumps({'url':'http://g.cn/',
                                'url_alias':[],
                                'filename':None}),
                  destination=self.options.queues.processed)

        stomp.disconnect()

        # start worker
        shot_service.logger = logging
        shot_service.cfg = self.options
        t = shot_service.ScreenshotWorker()

        t.start()
        t.postSetup('1')

        threading.Timer(5, self.end_test_shot).start()

        self.app.exec_()

    def test_sized_shot(self):
        self.pool_sema.acquire()

        # enqueue task
        stomp = stompy.simple.Client()
        stomp.connect()

        stomp.put(pickle.dumps({'url':'https://docs.google.com/Doc?docid=0AVI5kV_5NTU9ZGM0c2JrdjJfNjQzZnRqemhwZGs&hl=zh_CN',
                                'url_alias':[],
                                'filename':None,
                                'canvas_size':{'width':800,'height':1440}}),
                  destination=self.options.queues.processed)

        stomp.disconnect()

        # start worker
        shot_service.logger = logging
        shot_service.cfg = self.options
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
            stomp.subscribe(self.options.queues.shotted)
            try:
                m=stomp.get_nowait()
                self.assert_(m is not None)
            except stompy.simple.Client.Empty:
                self.fail
            stomp.unsubscribe(self.options.queues.shotted)

            stomp.subscribe(self.options.queues.cancel)
            try:
                m = stomp.get_nowait()
                self.fail("Got a canceld task..")
            except stompy.simple.Client.Empty:
                pass
            stomp.unsubscribe(self.options.queues.cancel)
        finally:
            stomp.disconnect()
            self.pool_sema.release()

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ScreenshotWorkerTest)
    unittest.TextTestRunner(verbosity=1).run(suite)

