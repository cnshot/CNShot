'''
Created on 2011-3-6

@author: yale
'''

import signal, os

class ProcessManager:
    def __init__(self, cfg, logger):
        self.cfg = cfg
        self.logger = logger
        self.workers = []
    
    def add(self, worker):
        self.workers.append(worker)
        
    def startAll(self):
        for w in self.workers:
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
        self.logger.warn("Child exited ...")
        for i in range(len(self.workers)):
            if self.workers[i].pid <= 0:
                continue
            self.logger.warn("Testing child %d: %d", i, self.workers[i].pid)
            try:
                done_pid = 0
                exit_status = 0
                done_pid, exit_status = os.waitpid(self.workers[i].pid,
                                                   os.WNOHANG)
            except OSError,e:
                self.logger.warn("Failed to waitpid: %d %s",
                            self.workers[i].pid,
                            str(e))
                done_pid = self.workers[i].pid
                pass
            if done_pid > 0:
                self.logger.warn("Child %d exited: %d %d", i, done_pid, exit_status)
                new_worker = self.workers[i].clone()
                new_worker._run()
                self.workers[i] = new_worker
                return
            
    def setSignal(self):
        signal.signal(signal.SIGINT, lambda s, f: self.killChildProcesses(s,f))
        signal.signal(signal.SIGTERM, lambda s, f: self.killChildProcesses(s,f))
        signal.signal(signal.SIGCHLD, lambda s, f: self.restartChildProcess(s,f))

class ProcessWorker(object):
    def __init__(self, cfg, logger, id='UNKNOWN'):
        self.cfg = cfg
        self.logger = logger
        self.id = id
        self.pid = -1
    
    def clone(self):
        return self.__class__(self.cfg, self.logger, self.id)
        
    def _run(self):
        pid = os.fork()
        if pid > 0:
            self.pid = pid
            return pid
        
        self.run()
        
    def run(self):
        pass