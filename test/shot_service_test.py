#!/usr/bin/python

import sys, os, subprocess, \
    signal, time, logging, logging.config, threading, pickle, signal, \
    unittest, \
    Queue, \
    stomp

from xml.dom import minidom

from PyQt4.QtCore import *
from PyQt4.QtGui import *

cwd = os.path.dirname(__file__)
if cwd == '':
    cwd = os.getcwd()
cwd=os.path.abspath(cwd)
sys.path.append(os.path.abspath(cwd + '/../'))
    
import shot_service

class DummyOptions(object):
    pass        

class MyListener(object):
    def __init__(self, callback):
        self.callback = callback

    def on_error(self, headers, message):
        print 'received an error %s' % message
        pass

    def on_message(self, headers, message):
        print 'received a message %s' % message
        self.callback(message)

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

        logging.basicConfig(level=logging.WARNING)

        # self.app = QApplication([])
        # signal.signal(signal.SIGINT, signal.SIG_DFL)

        self.pool_sema = threading.Semaphore(value=1)
        self.stomp_sema = threading.Semaphore(value=1)

        self.child_processes = []
        
    def tearDown(self):
        pass

    def killChildProcesses(self, signum, frame):
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        for pid in self.child_processes:
            os.kill(pid, signal.SIGINT)

        self.child_processes=[]
        return 0
        
    def page_shot_test(self, task, timeout=5, worker_lifetime=4, task_func=None,
                       workers=1, requests=1):
        self.pool_sema.acquire()
        if timeout <= worker_lifetime:
            timeout = worker_lifetime + 1

        # start worker
        shot_service.logger = logging
        shot_service.cfg = self.options

        # for n in range(workers):
        #     t = shot_service.ScreenshotWorker()
        #     t.start()
        #     t.postSetup(str(n))

        # enqueue task
        src_stomp = stomp.Connection()
        src_stomp.start()
        src_stomp.connect()
        for n in range(requests):
            src_stomp.send(pickle.dumps(task),
                           destination=self.options.queues.processed)
        src_stomp.disconnect()

        self.shoten_msgs = []
        shoten_conn = stomp.Connection()
        shoten_conn.set_listener('',
                                 MyListener(lambda x: self.shoten_msgs.append(x)))
        shoten_conn.start()
        shoten_conn.connect()
        shoten_conn.subscribe(destination=self.options.queues.shotted, ack='auto')

        self.cancel_msgs = []
        cancel_conn = stomp.Connection()
        cancel_conn.set_listener('',
                                 MyListener(lambda x: self.cancel_msgs.append(x)))
        cancel_conn.start()
        cancel_conn.connect()
        cancel_conn.subscribe(destination=self.options.queues.cancel, ack='auto')

        self.child_processes = []
        for n in range(workers):
            pid = shot_service.ShotProcessWorker(id=str(n), lifetime=worker_lifetime).run()
            self.child_processes.append(pid)
            
        signal.signal(signal.SIGINT, self.killChildProcesses)

        # threading.Timer(timeout, self.app.exit).start()
        # self.app.exec_()       

        time.sleep(timeout)

        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # resumed by self.app.exit()
        shoten_conn.disconnect()
        cancel_conn.disconnect()

        self.assert_(len(self.shoten_msgs) == requests,
                     "Got %d/%d shoten msg for task: %s" % (len(self.shoten_msgs), requests, task['url']))
        self.assert_(len(self.cancel_msgs) == 0, 
                     "Got %d/%d cancel msgs for task: %s" % (len(self.cancel_msgs), requests, task['url']))
        
        for m in self.shoten_msgs:
            returned_task = pickle.loads(str(m))
            print "Returned task URL: %s %s %s" % \
                (returned_task['url'],
                 returned_task['filename'],
                 returned_task['html_filename'])
        
            if task_func:
                task_func(returned_task)
            
        self.pool_sema.release()

    def readability(self, task):
        if not task['html_filename']:
            return

        content = subprocess.Popen(["/usr/bin/php",
                                    "../readability.php",
                                    "url=file://"+task['html_filename']],
                                   stdout=subprocess.PIPE).communicate()[0]
        # print content
        
        dom = minidom.parseString(content)
        print "Title: %s" % dom.getElementsByTagName("title")[0].firstChild.data
        try:
            print "Body: \n%s\n" % dom.getElementsByTagName("body")[0].firstChild.toxml()
        except AttributeError:
            print "No body."

    def test_shot(self):
        self.page_shot_test({'url':'http://g.cn',
                             'url_alias':[],
                             'filename':None},
                            worker_lifetime=5)

    def test_gb2312_shot(self):
        self.page_shot_test({'url':'http://news.sina.com.cn/w/2010-04-19/031320100881.shtml',
                             'url_alias':[],
                             'filename':None},
                            worker_lifetime=20, task_func=lambda x:self.readability(x))

    # def test_gb2312_shot(self):
    #     self.page_shot_test({'url':("file:%s/data/092120103860.shtml" % cwd),
    #                          'url_alias':[],
    #                          'filename':None},
    #                         worker_lifetime=5, task_func=lambda x:self.readability(x))
       
    # def test_sized_shot(self):
    #     self.page_shot_test({'url':'https://docs.google.com/Doc?docid=0AVI5kV_5NTU9ZGM0c2JrdjJfNjQzZnRqemhwZGs&hl=zh_CN',
    #                          'url_alias':[],
    #                          'filename':None,
    #                          'canvas_size':{'width':800,'height':1440}},
    #                         worker_lifetime=10, task_func=lambda x:self.readability(x))        

    # def test_jquery(self):
    #     self.page_shot_test({'url':'http://www.zhangxinxu.com/jq/jcarousel_zh/examples/dynamic_ajax.html',
    #                          'url_alias':[],
    #                          'filename':None},
    #                         worker_lifetime=5)

    # def test_concurrent_requests(self):
    #     self.page_shot_test({'url':'http://localhost/test/qwebframe.html',
    #                          'url_alias':[],
    #                          'filename':None},
    #                         worker_lifetime=20,
    #                         workers=5, requests=50)

if __name__ == '__main__':
#    logging.getLogger("shot_service_test").setLevel( logging.DEBUG )

    suite = unittest.TestLoader().loadTestsFromTestCase(ScreenshotWorkerTest)
    unittest.TextTestRunner(verbosity=1).run(suite)

