'''
Created on 2011-3-6

@author: yale
'''

import signal, os, setproctitle
import thread
from datetime import datetime, timedelta

from lts.models import ProcessWorker as PWM

class ProcessManager:
    def __init__(self, cfg, logger):
        self.cfg = cfg
        self.logger = logger
        self.workers = []
        self.signal_lock = thread.allocate_lock()
    
    def add(self, worker):
        self.workers.append(worker)
        
    def startAll(self):
        for w in self.workers:
            self.logger.info("Starting worker: %s", w.id)
            w._run()
    
    def killChildProcesses(self, signum, frame):
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    
        self.logger.info("Exiting with %d child processes ...", len(self.workers))
    
        try:
            for child in self.workers:
                self.logger.info("Killing child process: %s %d", child.id, child.pid)
                os.kill(child.pid, signal.SIGINT)
        except UnboundLocalError:
            exit(0)
    
        self.workers=[]
        exit(0)
    
    def restartChildProcess(self, signum, frame):
#        if(self.signal_lock.acquire()):
#            try:
        self.logger.warn("SIGCHLD detected ...")

        while True:
            done_pid = 0
                        
            try:
                self.logger.debug("Waitpid ...")
                done_pid, exit_status = os.waitpid(0, os.WNOHANG)
            except OSError,e:
                self.logger.warn("waitpid() failed: %s", str(e))
                
            if done_pid <= 0:
                self.logger.debug("No more exited child was found.")
                return
        
            exited_worker_indexs = filter(lambda i: self.workers[i].pid == done_pid,
                                          range(len(self.workers)))
        
            for i in exited_worker_indexs:
                self.logger.warn("Child %d %s exited: %d %d",
                                 i, self.workers[i].id, done_pid, exit_status)
                new_worker = self.workers[i].clone()
                self.logger.warn("Child %d %s cloned",
                                 i, self.workers[i].id)
                new_worker._run()
                self.workers[i] = new_worker
                self.logger.warn("Child %d %s restarted: %d",
                                 i, self.workers[i].id, self.workers[i].pid)

#            finally:
#                self.signal_lock.release()
            
        return
            
    def setSignal(self):
        signal.signal(signal.SIGINT, lambda s, f: self.killChildProcesses(s,f))
        signal.signal(signal.SIGTERM, lambda s, f: self.killChildProcesses(s,f))
        signal.signal(signal.SIGCHLD, lambda s, f: self.restartChildProcess(s,f))

class ProcessWorker(object):
    def __init__(self, cfg, logger, id='UNKNOWN', post_fork=None):
        self.cfg = cfg
        self.logger = logger
        self.id = id
        self.pid = -1
        self.post_fork = post_fork
        
    def clone(self):
        return self.__class__(self.cfg, self.logger, id=self.id,
                              post_fork=self.post_fork)
        
    def _run(self):
        pid = os.fork()
        if pid > 0:
            self.pid = pid
            return pid

        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

        from django.db import connection
        connection.close()

        try:
#            p = PWM.objects.get(sid = self.id)
#        except PWM.DoesNotExist:
#            p = PWM(sid=self.id)
#        except PWM.MultipleObjectsReturned:
            PWM.objects.filter(sid = self.id).delete()
        except PWM.DoesNotExist:
            pass
        
        p = PWM(sid=self.id)
            
        p.pid = os.getpid()
        p.last_start = datetime.now()
        p.last_success = datetime.now()
        p.save()
        
        setproctitle.setproctitle(self.id)
        if self.post_fork:
            f = self.post_fork
            f()
        self.run()
        
    def run(self):
        pass
    
    def jobDone(self):
        try:
            p = PWM.objects.get(sid = self.id)
        except PWM.DoesNotExist:
            self.logger.warn("No PWM was found for worker: %s", self.id)
            return
        
        p.last_success = datetime.now()
        p.save()
        
class RestartZombines:
    @classmethod
    def run(cls, _cfg, _logger):
        tt = datetime.now() - timedelta(seconds = _cfg.process_manager.success_limit)
        zombines = filter(lambda x: x.running(), PWM.objects.filter(last_success__lte=tt).filter(last_start__lte=tt))
        map(lambda x: _logger.info("Found zombine worker: %d %s", x.pid, x.sid), zombines)
        map(lambda x: x.kill(), zombines)
        