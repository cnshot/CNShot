#!/usr/bin/python

import sys, signal, xmlrpclib, pickle, stompy, tempfile, logging, logging.config

from Queue import Queue
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebPage

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

from optparse import OptionParser

options = None

class ScreenshotWorker(QThread):
    def __init__(self):
        self.task = None
        self.webpage = QWebPage()
        self.mutex = QMutex()
        self.processing = QWaitCondition()
        self.output_mq = None
        self.timer = QTimer(self.webpage)
        if options.dest_queue:
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

        logger.warn(self.objectName() + " Timeout")

        # enable task reader
        self.webpage.triggerAction(QWebPage.Stop)

        self.mutex.unlock()        

    def onLoadFinished(self, result):
        self.mutex.lock()

        try:
            self.timer.stop()
        except:
            pass

        if (self.webpage.bytesReceived() == 0) or self.task is None:
            logger.error(self.objectName() + " Request failed")
            if self.output_mq:
                # TODO: failure info
                pass
        else:
            logger.info(self.objectName() + " Page loaded: " + self.task['url'])

            # Set the size of the (virtual) browser window
            self.webpage.setViewportSize(self.webpage.mainFrame().contentsSize())

            # Paint this frame into an image
            qs = self.webpage.viewportSize()
            logger.debug(self.objectName() + " View port size: " + str(qs))
            if qs.width() > options.max_width:
                qs.setWidth(options.max_width)
#            if qs.width() < min_width:
#                qs.setWidth(min_width)
            if qs.height() > options.max_height:
                qs.setHeight(options.max_height)
#            if qs.height() < min_height:
#                qs.setHeight(min_height)
            logger.debug(self.objectName() + " Size to save: " + str(qs))
            image = QImage(qs, QImage.Format_ARGB32)
            painter = QPainter(image)

            logger.debug(self.objectName() + " Rendering URL: " + self.task['url'])

            self.webpage.mainFrame().render(painter)
            painter.end()

            logger.info(self.objectName() + " Saving file: " + self.task['filename'])

            image.save(self.task['filename'])

            logger.info(self.objectName() + " File saved: " + self.task['filename'])
            

            if self.output_mq:
                # success info
                try:
                    stomp = stompy.simple.Client()
                    stomp.connect()

                    stomp.put(pickle.dumps(self.task),
                              destination=options.dest_queue)
                finally:
                    try:
                        stomp.disconnect()
                    except:
                        logger.warn(self.objectName() + " Failed to enqueue finished task.")
                        pass
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
        logger.debug(self.objectName() + " onOpen: " + url)
        self.webpage.mainFrame().setHtml("<html></html>")
        self.webpage.setViewportSize(QSize(0,0))

        self.timer.start(options.timeout * 1000)

        QObject.connect(self.webpage, SIGNAL("loadFinished(bool)"), 
                        self.onLoadFinished, Qt.QueuedConnection)
        self.webpage.mainFrame().load(QUrl(url))

    def run(self):
        while True:
            self.mutex.lock()

            # wait for task done
            while self.task != None:
                self.processing.wait(self.mutex)

            try:
                # persistent stomp is unsafe :(
                stomp = stompy.simple.Client()
                stomp.connect()
                stomp.subscribe(options.source_queue, ack='client')
            except:
                logger.warn(self.objectName() + " STOMP subscribe failed.")
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
                logger.warn(self.objectName() + " STOMP dequeue failed.")
                self.mutex.unlock()
                continue
            finally:
                try:
                    stomp.unsubscribe(options.source_queue)
                    stomp.disconnect()
                except:
                    logger.warn(self.objectName() + " STOMP unsubscribe failed.")
                    pass

            self.task = pickle.loads(m.body)
            if self.task['filename'] is None:
                if sys.hexversion >= 0x02060000:
                    f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                else:
                    f = tempfile.NamedTemporaryFile(suffix='.png')
                self.task['filename'] = f.name
                f.close()

            logger.info(self.objectName() + " Run: " + self.task['url'])
            self.emit(SIGNAL("open"), self.task['url'])

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
    parser.add_option("-l", "--log-config",
                      dest="log_config", 
                      default="/etc/link_shot_tweet_log.conf",
                      type="string",
                      help="Logging config file [default: %default].",
                      metavar="LOG_CONFIG")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    logging.config.fileConfig(options.log_config)
    logger = logging.getLogger("shot_service")

    logger.info("Workers: " + str(options.workers))
    logger.info("Max width: " + str(options.max_width))
    logger.info("Max height: " + str(options.max_height))
    logger.info("Source queue: " + str(options.source_queue))
    logger.info("Dest queue: " + str(options.dest_queue))
    logger.info("Timeout: " + str(options.timeout))

    app = QApplication([])
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    ta = []

    for i in range(options.workers):
        t = ScreenshotWorker()
        t.start()
        t.postSetup(str(i))
        ta.append(t)

    sys.exit(app.exec_())
