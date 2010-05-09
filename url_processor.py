#!/usr/bin/python

import pycurl, StringIO, re, threading, time, logging, logging.config, \
    stompy, pickle, os, sys, socket, itertools

from optparse import OptionParser
from config import Config, ConfigMerger

from lts.models import ImageSitePattern, IgnoredSitePattern, \
    Link, Tweet, LinkShot, LinkRate, ShotPublish, SizedCanvasSitePattern

class TaskProcessingThread(threading.Thread):
    def __init__(self, task):
        threading.Thread.__init__(self)
        self.task = task

    def run(self):
        # processing shorten_url
        logger.info("Start to process task: %s", self.task['url'])
        known_urls = []

        while True:
            known_urls.append(self.task['url'])
            (c,h) = http_header(self.task['url'])
            if not h:
                break
            new_url = extend_url(h)
            if not new_url:
                break

            if new_url in known_urls:
                logger.warn("Loop in URL extending: %s %s",
                            self.task['url'], new_url)
                return

            # update link alias
            try:
                org_link = Link.objects.get(url=self.task['url'])
                try:
                    new_link = Link.objects.get(url=new_url)
                except Link.DoesNotExist:
                    new_link = Link(url=new_url)
                    new_link.save()
                org_link.alias_of=new_link
                org_link.save()
                LinkShot.objects.filter(link=org_link).update(link=new_link)
            except:
                logger.warn("Failed to get/update org_link: %s", self.task['url'])
                return

            # set alias
            if not self.task.has_key('url_alias'):
                self.task['url_alias'] = []
            self.task['url_alias'].append(self.task['url'])
            self.task['url'] = new_url

        # ignore links have shot already
        try:
            l = Link.objects.get(url=self.task['url'])
            if len(LinkShot.objects.filter(link=l))>0:
                logger.info("Skip shotted link: %s", l.url)
                self.writeMQ(cfg.queues.cancel, self.task)
                return
        except Link.DoesNotExist:
            logger.debug("Failed to get link: %s", self.task['url'])

        # accept mime type text or unknown
        mime_type = http_mime_type(h)
        if mime_type:
            if mime_type[0]!='text':
                logger.info("Ignore MIME type %s of URL: %s",
                            mime_type[1], self.task['url'])
                self.writeMQ(cfg.queues.cancel, self.task)
                return

        if patterns.ignore(self.task['url']):
            # enqueue cancel
            logger.info("Ingore URL: %s",
                        self.task['url'])            
            self.writeMQ(cfg.queues.cancel, self.task)
            return

        if patterns.image(self.task['url']):
            # enqueue cancel
            logger.info("Image URL: %s",
                        self.task['url'])                        
            self.writeMQ(cfg.queues.cancel, self.task)
            return
            
        canvas_pattern = patterns.sized_canvas(self.task['url'])
        if canvas_pattern:
            logger.debug("Canvas pattern obj: %s", dir(canvas_pattern))
            self.task['canvas_size'] = {
                'height':canvas_pattern.height,
                'width':canvas_pattern.width
                }

        # enqueue shot
        logger.info("Enqueue task for shot: %s", self.task['url'])
        self.writeMQ(cfg.queues.processed, self.task)

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
    def __init__(self):
#        conn = sqlite3.connect(db_filename)
#        c = conn.cursor()

        # ignored sites
#        c.execute('select * from ignore_site_patterns')
        self.ignore_patterns = map(lambda x: re.compile(x,re.M),
                                   [x.pattern for x in IgnoredSitePattern.objects.all()])

        # img sites
#        c.execute('select * from img_site_patterns')
        self.img_patterns = map(lambda x: re.compile(x,re.M),
                                [x.pattern for x in ImageSitePattern.objects.all()])

        # sized canvas sites
        self.sized_canvas_patterns = SizedCanvasSitePattern.objects.all()
        map(lambda x: setattr(x,'p',re.compile(x.pattern, re.M)), self.sized_canvas_patterns)

        # shorten url sites
#        c.execute('select * from shorten_url_patterns')
#        self.shorten_url_patterns = map(lambda x: re.compile(x,re.M),
#                                        [x[2] for x in c.fetchall()])
        
#        conn.close()

    def ignore(self, url):
        return any(map(lambda x: x.search(url), self.ignore_patterns))

    def image(self, url):
        return any(map(lambda x: x.search(url), self.img_patterns))

    # def shorten_url(self, url):
    #     return any(map(lambda x: x.search(url), self.shorten_url_patterns))

    def sized_canvas(self, url):
        try:
            return itertools.dropwhile(lambda x: not x.p.search(url), self.sized_canvas_patterns).next()
        except StopIteration:
            return None

def http_header(url):
    logger.debug("http_header: %s", url)

    c = pycurl.Curl()
    c.setopt(pycurl.NOSIGNAL, 1)
    c.setopt(pycurl.FOLLOWLOCATION, 0)
    c.setopt(pycurl.NOBODY, 1)
    c.setopt(pycurl.TIMEOUT, cfg.url_processor.timeout)
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

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("url_processor")

    patterns = URLPatterns()

    # loop, dequeue source, create processing thread
    if not cfg.queues.fetched:
        logger.error("Source queue is undefined.")
        exit(1)

    logger.info("Start URL processing.")

    while True:
        # persistent stomp is unsafe :(
        try:
            stomp = stompy.simple.Client()
            stomp.connect()
            stomp.subscribe(cfg.queues.fetched, ack='client')
        except (stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError):
            logger.warn("STOMP subscribe failed.")
            try:
                stomp.disconnect()
            except (stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError):
                pass
            continue

        try:
            m = stomp.get()
            stomp.ack(m)
            logger.debug("Got message: %s", m.body)
        except (stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError):
            logger.warn("STOMP dequeue failed.")
            continue
        finally:
            try:
                stomp.unsubscribe(cfg.queues.fetched)
                stomp.disconnect()
            except (stompy.stomp.ConnectionError, 
                    stompy.stomp.NotConnectedError,
                    socket.error):
                logger.warn("STOMP unsubscribe failed.")
                pass

        TaskProcessingThread(pickle.loads(m.body)).start()
        
