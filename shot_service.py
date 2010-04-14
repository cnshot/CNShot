#!/usr/bin/python

import sys, signal, xmlrpclib, pickle, stompy, tempfile, os, \
    logging, logging.config

from datetime import datetime
from Queue import Queue
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebPage

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

from optparse import OptionParser
from config import Config, ConfigMerger

class ScreenshotWorker(QThread):
    def __init__(self):
        self.task = None
        self.webpage = QWebPage()
        self.mutex = QMutex()
        self.processing = QWaitCondition()
        self.timer = QTimer(self.webpage)
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

        logger.warn("%s Timeout", self.objectName())

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
            logger.error("%s Request failed", self.objectName())
            if cfg.queues.cancel:
                # failure info
                self.writeMQ(cfg.queues.cancel, self.task)
        else:
            logger.info("%s Page loaded: %s", self.objectName(), self.task['url'])

            # Set the size of the (virtual) browser window
            self.webpage.setViewportSize(self.webpage.mainFrame().contentsSize())

            # Paint this frame into an image
            qs = self.webpage.viewportSize()
            logger.debug("%s View port size: %s", self.objectName(), str(qs))
            if qs.width() > cfg.shot_service.max_width:
                qs.setWidth(cfg.shot_service.max_width)
#            if qs.width() < min_width:
#                qs.setWidth(min_width)
            if qs.height() > cfg.shot_service.max_height:
                qs.setHeight(cfg.shot_service.max_height)
#            if qs.height() < min_height:
#                qs.setHeight(min_height)
            logger.debug("%s Size to save: %s", self.objectName(), str(qs))
            image = QImage(qs, QImage.Format_ARGB32)
            painter = QPainter(image)

            logger.debug("%s Rendering URL: %s",
                         self.objectName(), self.task['url'])

            self.webpage.mainFrame().render(painter)
            painter.end()

            logger.info("%s Saving file: %s",
                        self.objectName(), self.task['filename'])

            if image.save(self.task['filename']):
                logger.info("%s File saved: %s",
                            self.objectName(), self.task['filename'])

                if cfg.queues.shotted:
                    # success info
                    self.task['shot_time']=datetime.utcnow()
                    self.writeMQ(cfg.queues.shotted, self.task)
            else:
                logger.error("%s Failed to save file: %s",
                             self.objectName(), self.task['filename'])
                if cfg.queues.cancel:
                    # failure info
                    self.writeMQ(cfg.queues.cancel, self.task)

        # enable task reader
        self.task = None
        try:
            QObject.disconnect(self.webpage, SIGNAL("loadFinished(bool)"), 
                               self.onLoadFinished)
        except:
            pass

        self.processing.wakeOne()
        self.mutex.unlock()

    def writeMQ(self, queue, task):
        if not queue:
            return

        try:
            stomp = stompy.simple.Client()
            stomp.connect()

            stomp.put(pickle.dumps(task),
                      destination=queue)
        finally:
            try:
                stomp.disconnect()
            except:
                logger.warn("%s Failed to enqueue finished task.",
                            self.objectName())

    def onOpen(self, url):
        logger.debug("%s onOpen: %s", self.objectName(), url)
        self.webpage.mainFrame().setHtml("<html></html>")
        self.webpage.setViewportSize(QSize(0,0))

        self.timer.start(cfg.shot_service.timeout * 1000)

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
                stomp.subscribe(cfg.queues.processed, ack='client')
            except:
                logger.warn("%s STOMP subscribe failed.", self.objectName())
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
                logger.warn("%s STOMP dequeue failed.", self.objectName())
                self.mutex.unlock()
                continue
            finally:
                try:
                    stomp.unsubscribe(cfg.queues.processed)
                    stomp.disconnect()
                except:
                    logger.warn("%s STOMP unsubscribe failed.", self.objectName())
                    pass

            self.task = pickle.loads(m.body)
            if self.task['filename'] is None:
                if sys.hexversion >= 0x02060000:
                    f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                else:
                    f = tempfile.NamedTemporaryFile(suffix='.png')
                self.task['filename'] = f.name
                f.close()

            logger.info("%s Run: %s", self.objectName(), self.task['url'])
            self.emit(SIGNAL("open"), self.task['url'])

            self.mutex.unlock()

if __name__ == '__main__':
    description = '''Screenshot service with QtPt.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)
    
    # parser.add_option("-n", "--workers", 
    #                   dest="workers", default=4, type="int",
    #                   help="Number or worker threads [default: %default].",
    #                   metavar="WORKERS")
    # parser.add_option("-w", "--max-width", 
    #                   dest="max_width", default=2048, type="int",
    #                   help="Max width of the screenshot image [default: %default].",
    #                   metavar="MAX_WIDTH")
#    parser.add_option("--min-width", 
#                      dest="min_width", default=640, type="int",
#                      help="Min width of the screenshot image [default: %default].",
#                      metavar="MAX_WIDTH")
    # parser.add_option("-g", "--max-height", 
    #                   dest="max_height", default=4096, type="int",
    #                   help="Max height of the screenshot image [default: %default].",
    #                   metavar="MAX_HEIGHT")
#    parser.add_option("--min-height", 
#                      dest="min_height", default=480, type="int",
#                      help="Min height of the screenshot image [default: %default].",
#                      metavar="MIN_HEIGHT")
    # parser.add_option("-t", "--timeout", 
    #                   dest="timeout", default=20, type="int",
    #                   help="Timeout of page loading in second [default: %default].",
    #                   metavar="TIMEOUT")
    # parser.add_option("-s", "--source-queue",
    #                   dest="source_queue", default="/queue/shot_service",
    #                   type="string",
    #                   help="Source message queue path [default: %default].",
    #                   metavar="SOURCE_QUEUE")
    # parser.add_option("-d", "--dest-queue", 
    #                   dest="dest_queue", default="/queue/shot_dest",
    #                   type="string",
    #                   help="Dest message queue path [default: %default].",
    #                   metavar="DEST_QUEUE")
    # parser.add_option("-c", "--cancel-queue",
    #                   dest="cancel_queue", default="/queue/cancel",
    #                   type="string",
    #                   help="Message queue of tasks to cancel [default: %default].",
    #                   metavar="CANCEL_QUEUE")
    # parser.add_option("-l", "--log-config",
    #                   dest="log_config", 
    #                   default="/etc/link_shot_tweet_log.conf",
    #                   type="string",
    #                   help="Logging config file [default: %default].",
    #                   metavar="LOG_CONFIG")

    parser.add_option("-c", "--config",
                      dest="config",
                      default="lts.cfg",
                      type="string",
                      help="Config file [default %default].",
                      metavar="CONFIG")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    cfg=Config(file(filter(lambda x: os.path.isfile(x),
                           [options.config,
                            os.path.expanduser('~/.lts.cfg'),
                            '/etc/lts.cfg'])[0]))
    # cfg.addNamespace(options,'common')

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("shot_service")

    logger.info("Workers: %d", cfg.shot_service.workers)
    logger.info("Max width: %d", cfg.shot_service.max_width)
    logger.info("Max height: %d", cfg.shot_service.max_height)
    logger.info("Source queue: %s", cfg.queues.processed)
    logger.info("Dest queue: %s", cfg.queues.shotted)
    logger.info("Timeout: %d", cfg.shot_service.timeout)

    app = QApplication([])
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    ta = []

    for i in range(cfg.shot_service.workers):
        t = ScreenshotWorker()
        t.start()
        t.postSetup(str(i))
        ta.append(t)

    sys.exit(app.exec_())
