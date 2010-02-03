#!/usr/bin/python

import sys
import signal

from Queue import Queue
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebPage

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

from optparse import OptionParser

num_screenshot_threads = 1
max_width = 2048
max_height = 4096

source_queue = Queue()
screenshot_queue = Queue()

class ScreenshotWorker(QThread):
    def __init__(self):
        self.task = None
        self.webpage = QWebPage()
        self.mutex = QMutex()
        self.processing = QWaitCondition()
        QThread.__init__(self)

    def postSetup(self, name):
        # Called by main after start()
        QObject.connect(self, SIGNAL("open"), self.onOpen, Qt.QueuedConnection)
        self.setObjectName(name)

    def onLoadFinished(self, result):
        self.mutex.lock()
        if not result:
            print(self.objectName() + " Request failed")
        else:
            print(self.objectName() + " Page loaded: " + self.task['url'])

            # Set the size of the (virtual) browser window
            self.webpage.setViewportSize(self.webpage.mainFrame().contentsSize())

            # Paint this frame into an image
            qs = self.webpage.viewportSize()
            print(self.objectName() + " View port size: " + str(qs))
            if qs.width() > max_width:
                qs.setWidth(max_width)
            if qs.height() > max_height:
                qs.setHeight(max_height)
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

        # enable task reader
        self.task = None
        QObject.disconnect(self.webpage, SIGNAL("loadFinished(bool)"), self.onLoadFinished)

        self.processing.wakeOne()
        self.mutex.unlock()

    def onOpen(self, url):
        print("onOpen: " + url)
        self.webpage.mainFrame().setHtml("<html></html>")
        self.webpage.setViewportSize(QSize(0,0))

        QObject.connect(self.webpage, SIGNAL("loadFinished(bool)"), self.onLoadFinished, Qt.QueuedConnection)
        self.webpage.mainFrame().load(QUrl(url))

    def run(self):
        while True:
            self.mutex.lock()

            # wait for task done
            while self.task != None:
                self.processing.wait(self.mutex)

            self.task = source_queue.get()
            print("Run: " + self.task['url'])
            self.emit(SIGNAL("open"), self.task['url'])
            source_queue.task_done()
            self.mutex.unlock()

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

def ScreenShot(url, filename):
    import tempfile
    if filename is None:
        f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        filename = f.name
        f.close()
    print("ScreenShot: " + filename)
    source_queue.put({'url':url, 'filename':filename})
    return True

class RPCThread(QThread):
    def run(self):
        server = SimpleXMLRPCServer(("localhost", 8000), 
                                    requestHandler=RequestHandler,
                                    allow_none=True)
        server.register_introspection_functions()
        server.register_function(ScreenShot)
        server.serve_forever()

if __name__ == '__main__':
    qtargs = [sys.argv[0]]
    description = '''Screenshot service with QtPt.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)
    
    parser.add_option("-n", "--workers", dest="workers", default=4, type="int",
                      help="Number or worker threads [default: %default].",
                      metavar="WORKERS")
    parser.add_option("-w", "--max-width", dest="max_width", default=2048, type="int",
                      help="Max width of the screenshot image [default: %default].",
                      metavar="MAX_WIDTH")
    parser.add_option("-g", "--max-height", dest="max_height", default=4096, type="int",
                      help="Max height of the screenshot image [default: %default].",
                      metavar="MAX_HEIGHT")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    num_screenshot_threads = options.workers
    max_width = options.max_width
    max_height = options.max_height

    print("Workers: " + str(num_screenshot_threads))
    print("Max width: " + str(max_width))
    print("Max height: " + str(max_height))

    app = QApplication([])
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    ta = []

    for i in range(num_screenshot_threads):
        t = ScreenshotWorker()
        t.start()
        t.postSetup(str(i))
        ta.append(t)

    rpc_thread = RPCThread()
    rpc_thread.start()

    sys.exit(app.exec_())
