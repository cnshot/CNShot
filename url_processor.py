#!/usr/bin/python

import pycurl, StringIO, re, threading, time, sqlite3, logging, logging.config
import stompy, pickle

from optparse import OptionParser

class TaskProcessingThread(threading.Thread):
    def __init__(self, task):
        threading.Thread.__init__(self)
        self.task = task

    def run(self):
        # processing shorten_url
        logger.info("Start to process task: %s", self.task['url'])

        while True:
            (c,h) = http_header(self.task['url'])
            if not h:
                break
            new_url = extend_url(h)
            if not new_url:
                break

            # set alias
            if not self.task.has_key('url_alias'):
                self.task['url_alias'] = []
            self.task['url_alias'].append(self.task['url'])
            self.task['url'] = new_url

        # accept mime type text or unknown
        mime_type = http_mime_type(h)
        if mime_type:
            if mime_type[0]!='text':
                logger.info("Ignore MIME type %s of URL: %s",
                            mime_type[1], self.task['url'])
                self.writeMQ(options.cancel_queue, self.task)
                return

        if patterns.ignore(self.task['url']):
            # enqueue cancel
            logger.info("Ingore URL: %s",
                        self.task['url'])            
            self.writeMQ(options.cancel_queue, self.task)
            return

        if patterns.image(self.task['url']):
            # enqueue cancel
            logger.info("Image URL: %s",
                        self.task['url'])                        
            self.writeMQ(options.cancel_queue, self.task)
            return
            
        # enqueue shot
        logger.info("Enqueue task for shot: %s", self.task['url'])
        self.writeMQ(options.shot_queue, self.task)

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

class URLPatterns:
    def __init__(self, db_filename):
        conn = sqlite3.connect(db_filename)
        c = conn.cursor()

        # ignored sites
        c.execute('select * from ignore_site_patterns')
        self.ignore_patterns = map(lambda x: re.compile(x,re.M),
                                   [x[2] for x in c.fetchall()])

        # img sites
        c.execute('select * from img_site_patterns')
        self.img_patterns = map(lambda x: re.compile(x,re.M),
                                [x[2] for x in c.fetchall()])

        # shorten url sites
        c.execute('select * from shorten_url_patterns')
        self.shorten_url_patterns = map(lambda x: re.compile(x,re.M),
                                        [x[2] for x in c.fetchall()])
        
        conn.close()

    def ignore(self, url):
        return any(map(lambda x: x.search(url), self.ignore_patterns))

    def image(self, url):
        return any(map(lambda x: x.search(url), self.img_patterns))

    def shorten_url(self, url):
        return any(map(lambda x: x.search(url), self.shorten_url_patterns))

def http_header(url):
    logger.debug("http_header: %s", url)

    c = pycurl.Curl()
    c.setopt(pycurl.NOSIGNAL, 1)
    c.setopt(pycurl.FOLLOWLOCATION, 0)
    c.setopt(pycurl.NOBODY, 1)
    c.setopt(pycurl.TIMEOUT, options.timeout)
    c.setopt(pycurl.URL, str(url))
    c.setopt(pycurl.HTTPHEADER, ["Accept:"])
    h = StringIO.StringIO()
    b = StringIO.StringIO()
    c.setopt(pycurl.HEADERFUNCTION, h.write)
    c.setopt(pycurl.WRITEFUNCTION, b.write)

    try:
        c.perform()
    except pycurl.error, err:
        logger.error("Failed to fetch HTTP header: %s", url)
        return (None,None)

    logger.debug("%s", h.getvalue())

    return (c.getinfo(pycurl.HTTP_CODE), h.getvalue())

def http_mime_type(s):
    if not s:
        return None

    location_pattern = re.compile('^Content-Type:\s+(\w+)/(\w+)',re.M)
    m = re.search(location_pattern, s)
    if not m:
        return None
    
    return [m.group(1),m.group(2)]

def extend_url(s):
    if not s:
        return None

    location_pattern = re.compile('^Location:\s+(.*)$',re.M)
    m = re.search(location_pattern, s)
    if not m:
        return None
    
    return m.group(1).rstrip()
    
if __name__ == '__main__':
    description = '''Shot task URL pre-processor.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-s", "--source-queue",
                      dest="source_queue", default="/queue/url_processor",
                      type="string",
                      help="Source message queue path [default: %default].",
                      metavar="SOURCE_QUEUE")

    parser.add_option("-t", "--shot-queue",
                      dest="shot_queue", default="/queue/shot_service",
                      type="string",
                      help="Message queue path for shot [default: %default].",
                      metavar="SHOT_QUEUE")

    parser.add_option("-d", "--dest-queue", 
                      dest="dest_queue", default="/queue/shot_dest",
                      type="string",
                      help="Dest message queue path [default: %default].",
                      metavar="DEST_QUEUE")

    parser.add_option("-c", "--cancel-queue",
                      dest="cancel_queue", default="/queue/cancel",
                      type="string",
                      help="Message queue of tasks to cancel [default: %default].",
                      metavar="CANCEL_QUEUE")

    parser.add_option("-p", "--pattern-db", 
                      dest="pattern_db", default="link_tweet_shot.sqlite",
                      type="string",
                      help="URL pattern database file [default: %default].",
                      metavar="PATTERN_DB")

    parser.add_option("--timeout", 
                      dest="timeout", default=20, type="int",
                      help="Timeout of HTTP request in second [default: %default].",
                      metavar="TIMEOUT")

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
    logger = logging.getLogger("url_processor")

    patterns = URLPatterns(options.pattern_db)

    # loop, dequeue source, create processing thread
    if not options.source_queue:
        logger.error("Source queue is undefined.")
        exit(1)

    logger.info("Start URL processing.")

    while True:
        # persistent stomp is unsafe :(
        try:
            stomp = stompy.simple.Client()
            stomp.connect()
            stomp.subscribe(options.source_queue, ack='client')
        except stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError:
            logger.warn("STOMP subscribe failed.")
            try:
                stomp.disconnect()
            except stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError:
                pass
            continue

        try:
            m = stomp.get()
            stomp.ack(m)
            logger.debug("Got message: %s", m.body)
        except stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError:
            logger.warn("STOMP dequeue failed.")
            continue
        finally:
            try:
                stomp.unsubscribe(options.source_queue)
                stomp.disconnect()
            except stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError:
                logger.warn("STOMP unsubscribe failed.")
                pass

        TaskProcessingThread(pickle.loads(m.body)).start()
        
