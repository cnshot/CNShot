#!/usr/bin/python

import sys
import signal

from Queue import Queue
from threading import Thread

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebPage

num_screenshot_threads = 4

def screenshot_worker():
    task = None

    app = QApplication(sys.argv)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    webpage = QWebPage()
#    webpage = page_queue.get()
#    page_queue.task_done()

    def onLoadFinished(result):
        if not result:
            print "Request failed"
            sys.exit(1)

        print("Page loaded: " + task['url'])

        # Set the size of the (virtual) browser window
        webpage.setViewportSize(webpage.mainFrame().contentsSize())

        # Paint this frame into an image
        image = QImage(webpage.viewportSize(), QImage.Format_ARGB32)
        painter = QPainter(image)
        webpage.mainFrame().render(painter)
        painter.end()
        image.save(task['filename'])
        screenshot_queue.put(task)

    webpage.connect(webpage, SIGNAL("loadFinished(bool)"), onLoadFinished)
    while True:
        global source_queue
        task = source_queue.get()
        print(task['url'])
        webpage.mainFrame().load(QUrl(task['url']))
        source_queue.task_done()

def source():
    return [
#        {'url':'http://g.cn/', 'filename':'/tmp/g.png'},
#        {'url':'http://news.sina.com.cn', 'filename':'/tmp/sina.png'},
        {'url':'file:///usr/share/doc/python-doc/html/contents.html','filename':'/tmp/contents.png'},
        {'url':'file:///usr/share/doc/python-doc/html/index.html','filename':'/tmp/index.png'},
        ]

source_queue = Queue()
page_queue = Queue()
screenshot_queue = Queue()

#app = QApplication(sys.argv)
#signal.signal(signal.SIGINT, signal.SIG_DFL)

for i in range(num_screenshot_threads):
#    page_queue.put(QWebPage())
    t = Thread(target=screenshot_worker)
    t.setDaemon(True)
    t.start()

for item in source():
    source_queue.put(item)

source_queue.join()  
