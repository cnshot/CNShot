#!/usr/bin/python

import sys
import signal

from Queue import Queue
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebPage

num_screenshot_threads = 4
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
        QObject.connect(self.webpage, SIGNAL("loadFinished(bool)"), self.onLoadFinished, Qt.QueuedConnection)
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
            if qs.width() > 2048:
                qs.setWidth(2048)
            if qs.height() > 4096:
                qs.setHeight(4096)
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
        self.processing.wakeOne()
        self.mutex.unlock()

    def onOpen(self, url):
        print("onOpen: " + url)
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

def source():
    return [
        {'url':'http://g.cn/', 'filename':'/tmp/g.png'},
        {'url':'http://news.sina.com.cn', 'filename':'/tmp/sina.png'},
        {'url':'file:///usr/share/doc/python-doc/html/contents.html','filename':'/tmp/contents.png'},
        {'url':'file:///usr/share/doc/python-doc/html/index.html','filename':'/tmp/index.png'},
        {'url':'http://www.tianya.cn/publicforum/content/funinfo/1/1801508.shtml', 'filename':'/tmp/tianya.png'},
        {'url':'http://news.mop.com/pic/hz/index.shtml', 'filename':'/tmp/mop.png'},
        ]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    for i in range(num_screenshot_threads):
        t = ScreenshotWorker()
        t.start()
        t.postSetup(str(i))

    for item in source():
        source_queue.put(item)

    sys.exit(app.exec_())
