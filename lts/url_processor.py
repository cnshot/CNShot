#!/usr/bin/python

import pycurl, StringIO, re, threading, stompy, pickle, itertools, socket

from urlparse import urljoin
from IPy import IP
from urlparse import urlparse

from lts.models import ImageSitePattern, IgnoredSitePattern, Link, LinkShot, \
    SizedCanvasSitePattern
from lts.process_manager import ProcessWorker

class TaskProcessingThread(threading.Thread):
    def __init__(self, task, patterns, cfg, logger, jobdone=None):
        threading.Thread.__init__(self)
        self.task = task
        self.patterns = patterns
        self.cfg = cfg
        self.logger = logger
        self.jobdone = jobdone

    def run(self):
        
        def extend_url(s):
            if not s:
                return None
        
            location_pattern = re.compile('^Location:\s+(.*)$',re.M)
            m = re.search(location_pattern, s)
            if not m:
                return None
            
            return m.group(1).rstrip()
        
        def http_mime_type(s):
            if not s:
                return None
        
            location_pattern = re.compile('^Content-Type:\s+(\w+)/(\w+)',re.M)
            m = re.search(location_pattern, s)
            if not m:
                return None
            
            return [m.group(1),m.group(2)]

        def http_header(url):
            self.logger.debug("http_header: %s", url)
        
            c = pycurl.Curl()
            c.setopt(pycurl.NOSIGNAL, 1)
            c.setopt(pycurl.FOLLOWLOCATION, 0)
            c.setopt(pycurl.NOBODY, 1)
            c.setopt(pycurl.TIMEOUT, self.cfg.url_processor.timeout)
            c.setopt(pycurl.URL, str(url))
            c.setopt(pycurl.HTTPHEADER, ["Accept:"])
            h = StringIO.StringIO()
            b = StringIO.StringIO()
            c.setopt(pycurl.HEADERFUNCTION, h.write)
            c.setopt(pycurl.WRITEFUNCTION, b.write)
        
            try:
                c.perform()
            except pycurl.error:
                self.logger.error("Failed to fetch HTTP header: %s", url)
                return (None,None)
        
            self.logger.debug("%s", h.getvalue())
        
            return (c.getinfo(pycurl.HTTP_CODE), h.getvalue())
        
        # processing shorten_url
        self.logger.info("Start to process task: %s", self.task['url'])
        known_urls = []

        while True:
            known_urls.append(self.task['url'])
            (c,h) = http_header(self.task['url'])
            if not h:
                break
            new_url = extend_url(h)
            if not new_url:
                break
            new_url = urljoin(self.task['url'], new_url)

            if new_url in known_urls:
                self.logger.warn("Loop in URL extending: %s %s",
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
                self.logger.warn("Failed to get/update org_link: %s", self.task['url'])
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
                self.logger.info("Skip shotted link: %s", l.url)
                self.writeMQ(self.cfg.queues.cancel, self.task)
                return
        except Link.DoesNotExist:
            self.logger.debug("Failed to get link: %s", self.task['url'])

        # accept mime type text or unknown
        mime_type = http_mime_type(h)
        if mime_type:
            if mime_type[0]!='text':
                self.logger.info("Ignore MIME type %s of URL: %s",
                            mime_type[1], self.task['url'])
                self.writeMQ(self.cfg.queues.cancel, self.task)
                self.jobdone()
                return

        if self.patterns.ignore(self.task['url']):
            # enqueue cancel
            self.logger.info("Ignore URL: %s",
                        self.task['url'])            
            self.writeMQ(self.cfg.queues.cancel, self.task)
            self.jobdone()
            return

        if self.patterns.image(self.task['url']):
            # enqueue cancel
            self.logger.info("Image URL: %s",
                        self.task['url'])                        
            self.writeMQ(self.cfg.queues.cancel, self.task)
            self.jobdone()
            return
            
        canvas_pattern = self.patterns.sized_canvas(self.task['url'])
        if canvas_pattern:
            self.logger.debug("Canvas pattern obj: %s", dir(canvas_pattern))
            self.task['canvas_size'] = {
                'height':canvas_pattern.height,
                'width':canvas_pattern.width
                }

        # enqueue shot
        self.logger.info("Enqueue task for shot: %s", self.task['url'])
        self.writeMQ(self.cfg.queues.processed, self.task)
        self.jobdone()

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
                self.logger.warn("%s Failed to enqueue finished task.",
                            self.objectName())

class URLPatterns:
    def __init__(self, cfg, logger):
        self.cfg = cfg
        self.logger = logger
        
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

        self.denied_networks = []
        for n in cfg.url_processor.denied_networks:
            self.denied_networks.append(IP(n))

        # shorten url sites
#        c.execute('select * from shorten_url_patterns')
#        self.shorten_url_patterns = map(lambda x: re.compile(x,re.M),
#                                        [x[2] for x in c.fetchall()])
        
#        conn.close()

    def ignore(self, url):
        if any(map(lambda x: x.search(url), self.ignore_patterns)):
            return True

        pr = urlparse(url)
        ip = IP(socket.gethostbyname(pr.hostname))
        for n in self.denied_networks:
            if ip in n:
                self.logger.info("Found IP %s in denined network %s: %s",
                            ip, n, url)
                return True

        return False

    def image(self, url):
        return any(map(lambda x: x.search(url), self.img_patterns))

    # def shorten_url(self, url):
    #     return any(map(lambda x: x.search(url), self.shorten_url_patterns))

    def sized_canvas(self, url):
        try:
            return itertools.dropwhile(lambda x: not x.p.search(url), self.sized_canvas_patterns).next()
        except StopIteration:
            return None
            
class URLProcessWorker(ProcessWorker):
    def __init__(self, cfg, logger, id='UNKNOWN', post_fork=None):
        super(URLProcessWorker, self).__init__(cfg, logger, id=id,
                                                post_fork=post_fork)
        self.lock = threading.Lock()
    
    def jobDone(self):
        self.lock.acquire()
        super(URLProcessWorker, self).jobDone()
        self.lock.release()
    
    def run(self):
        patterns = URLPatterns(self.cfg, self.logger)
    
        # loop, dequeue source, create processing thread
        if not self.cfg.queues.fetched:
            self.logger.error("Source queue is undefined.")
            return 1
    
        self.logger.info("Start URL processing.")
    
        while True:
            # persistent stomp is unsafe :(
            try:
                stomp = stompy.simple.Client()
                stomp.connect()
                stomp.subscribe(self.cfg.queues.fetched, ack='client')
            except (stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError):
                self.logger.warn("STOMP subscribe failed.")
                try:
                    stomp.disconnect()
                except (stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError):
                    pass
                continue
    
            try:
                m = stomp.get()
                stomp.ack(m)
                self.logger.debug("Got message: %s", m.body)
            except (stompy.stomp.ConnectionError, stompy.stomp.NotConnectedError):
                self.logger.warn("STOMP dequeue failed.")
                continue
            finally:
                try:
                    stomp.unsubscribe(self.cfg.queues.fetched)
                    stomp.disconnect()
                except (stompy.stomp.ConnectionError, 
                        stompy.stomp.NotConnectedError,
                        socket.error):
                    self.logger.warn("STOMP unsubscribe failed.")
                    pass
    
            try:
                TaskProcessingThread(pickle.loads(m.body), patterns, self.cfg,
                                     self.logger, jobdone=lambda:self.jobDone()).start()
            except TypeError, e:
                self.logger.error("Failed to start processing thread: %s", e)
                self.logger.error("Message body: %s", m.body)

