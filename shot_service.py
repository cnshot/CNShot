#!/usr/bin/python

import sys
import signal
import xmlrpclib
import pickle
import stompy
import tempfile

from Queue import Queue
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebPage

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

from optparse import OptionParser

num_screenshot_threads = 1
max_width = 2048
#min_width = 640
max_height = 4096
#min_height = 480
dest_mq = "/queue/shot_dest"
source_mq = "/queue/shot_source"
timeout = 10

#source_queue = Queue()
screenshot_queue = Queue()

class ScreenshotWorker(QThread):
    def __init__(self):
        self.task = None
        self.webpage = QWebPage()
        self.mutex = QMutex()
        self.processing = QWaitCondition()
        self.output_mq = None
        self.timer = QTimer(self.webpage)
        if dest_mq:
            self.output_mq = stompy.simple.Client()
            self.output_mq.connect()
        QThread.__init__(self)

    def postSetup(self, name):
        # Called by main after start()
        QObject.connect(self, SIGNAL("open"), 
                        self.onOpen, Qt.QueuedConnection)
        QObject.connect(self.timer, SIGNAL("timeout()"),
                        self.onTimer, Qt.QueuedConnection)
        self.setObjectName(name)

    def onTimer(self):
        self.mutex.lock()

        print(self.objectName() + " Timeout")

        # enable task reader
#        QObject.disconnect(self.webpage, SIGNAL("loadFinished(bool)"), 
#                           self.onLoadFinished)

#        self.task = None
        self.webpage.triggerAction(QWebPage.Stop)

#        self.processing.wakeOne()
        self.mutex.unlock()        

    def onLoadFinished(self, result):
        self.mutex.lock()

        try:
            self.timer.stop()
        except:
            pass

        if (self.webpage.bytesReceived() == 0) or self.task is None:
            print(self.objectName() + " Request failed")
            if self.output_mq:
                # TODO: failure info
                pass
        else:
            print(self.objectName() + " Page loaded: " + self.task['url'])

            # Set the size of the (virtual) browser window
            self.webpage.setViewportSize(self.webpage.mainFrame().contentsSize())

            # Paint this frame into an image
            qs = self.webpage.viewportSize()
            print(self.objectName() + " View port size: " + str(qs))
            if qs.width() > max_width:
                qs.setWidth(max_width)
#            if qs.width() < min_width:
#                qs.setWidth(min_width)
            if qs.height() > max_height:
                qs.setHeight(max_height)
#            if qs.height() < min_height:
#                qs.setHeight(min_height)
            print(self.objectName() + " Size to save: " + str(qs))
            image = QImage(qs, QImage.Format_ARGB32)
            painter = QPainter(image)

            print(self.objectName() + " Rendering URL: " + self.task['url'])

            self.webpage.mainFrame().render(painter)
            painter.end()

            print(self.objectName() + " Saving file: " + self.task['filename'])

            image.save(self.task['filename'])

            print(self.objectName() + " File saved: " + self.task['filename'])
            
            global screenshot_queue
            screenshot_queue.put(self.task)

            if self.output_mq:
                # TODO: success info
                pass

        # enable task reader
        self.task = None
        try:
            QObject.disconnect(self.webpage, SIGNAL("loadFinished(bool)"), 
                               self.onLoadFinished)
        except:
            pass

        self.processing.wakeOne()
        self.mutex.unlock()

    def onOpen(self, url):
        print(self.objectName() + " onOpen: " + url)
        self.webpage.mainFrame().setHtml("<html></html>")
        self.webpage.setViewportSize(QSize(0,0))

#        QObject.connect(self.timer, SIGNAL("timeout()"),
#                        self.onTimer, Qt.QueuedConnection)
        self.timer.start(timeout * 1000)

        QObject.connect(self.webpage, SIGNAL("loadFinished(bool)"), 
                        self.onLoadFinished, Qt.QueuedConnection)
        self.webpage.mainFrame().load(QUrl(url))

    def run(self):
        while True:
            self.mutex.lock()

            # wait for task done
            while self.task != None:
                self.processing.wait(self.mutex)

#            self.task = source_queue.get()
            try:
                # persistent stomp is unsafe :(
                stomp = stompy.simple.Client()
                stomp.connect()
                stomp.subscribe(source_mq, ack='client')
            except:
                print(self.objectName() + " STOMP subscribe failed.")
                try:
                    stomp.disconnect()
                except:
                    pass
                self.mutex.unlock()
                continue

            try:
                m=stomp.get()
                stomp.ack(m)
            except:
                print(self.objectName() + " STOMP dequeue failed.")
                self.mutex.unlock()
                continue
            finally:
                try:
                    stomp.unsubscribe(source_mq)
                    stomp.disconnect()
                except:
                    print(self.objectName() + " STOMP unsubscribe failed.")
                    pass

            self.task = pickle.loads(m.body)
            if self.task['filename'] is None:
                if sys.hexversion >= 0x02060000:
                    f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                else:
                    f = tempfile.NamedTemporaryFile(suffix='.png')
                self.task['filename'] = f.name
                f.close()

            print("Run: " + self.task['url'])
            self.emit(SIGNAL("open"), self.task['url'])

#            source_queue.task_done()
            self.mutex.unlock()

if __name__ == '__main__':
    description = '''Screenshot service with QtPt.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)
    
    parser.add_option("-n", "--workers", 
                      dest="workers", default=4, type="int",
                      help="Number or worker threads [default: %default].",
                      metavar="WORKERS")
    parser.add_option("-w", "--max-width", 
                      dest="max_width", default=2048, type="int",
                      help="Max width of the screenshot image [default: %default].",
                      metavar="MAX_WIDTH")
#    parser.add_option("--min-width", 
#                      dest="min_width", default=640, type="int",
#                      help="Min width of the screenshot image [default: %default].",
#                      metavar="MAX_WIDTH")
    parser.add_option("-g", "--max-height", 
                      dest="max_height", default=4096, type="int",
                      help="Max height of the screenshot image [default: %default].",
                      metavar="MAX_HEIGHT")
#    parser.add_option("--min-height", 
#                      dest="min_height", default=480, type="int",
#                      help="Min height of the screenshot image [default: %default].",
#                      metavar="MIN_HEIGHT")
    parser.add_option("-t", "--timeout", 
                      dest="timeout", default=20, type="int",
                      help="Timeout of page loading in second [default: %default].",
                      metavar="TIMEOUT")
    parser.add_option("-s", "--source-queue",
                      dest="source_queue", default="/queue/shot_source",
                      type="string",
                      help="Source message queue path [default: %default].",
                      metavar="SOURCE_QUEUE")
    parser.add_option("-d", "--dest-queue", 
                      dest="dest_queue", default="/queue/shot_dest",
                      type="string",
                      help="Dest message queue path [default: %default].",
                      metavar="DEST_QUEUE")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    num_screenshot_threads = options.workers
    max_width = options.max_width
 #   min_width = options.min_width
    max_height = options.max_height
 #   min_height = options.min_height
    source_mq = options.source_queue
    dest_mq = options.dest_queue
    timeout = options.timeout

    print("Workers: " + str(num_screenshot_threads))
    print("Max width: " + str(max_width))
    print("Max height: " + str(max_height))
    print("Source queue: " + str(source_mq))
    print("Dest queue: " + str(dest_mq))
    print("Timeout: " + str(timeout))

    app = QApplication([])
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    ta = []

    for i in range(num_screenshot_threads):
        t = ScreenshotWorker()
        t.start()
        t.postSetup(str(i))
        ta.append(t)

    sys.exit(app.exec_())
