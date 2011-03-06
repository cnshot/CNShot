'''
Created on 2011-3-6

@author: yale
'''

import signal, os

global logger

class ProcessManager:
    child_processes = []
    
    def __init__(self, cfg, logger):
        self.cfg = cfg
        self.logger = logger
    
    def killChildProcesses(self, signum, frame):
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    
        self.logger.info("Exiting with %d child processes ...", len(self.child_processes))
    
        try:
            for child in self.child_processes:
                self.logger.info("Killing child process: %d", child['pid'])
                os.kill(child['pid'], signal.SIGINT)
        except UnboundLocalError:
            exit(0)
    
        self.child_processes=[]
        exit(0)
    
    def restartChildProcess(self, signum, frame):
        self.self.logger.warn("Child exited ...")
        for i in range(len(self.child_processes)):
            if self.child_processes[i]['pid'] == 0:
                continue
            self.logger.warn("Testing child %d: %d", i, self.child_processes[i]['pid'])
            try:
                done_pid = 0
                exit_status = 0
                done_pid, exit_status = os.waitpid(self.child_processes[i]['pid'],
                                                   os.WNOHANG)
            except OSError,e:
                self.logger.warn("Failed to waitpid: %d %s",
                            self.child_processes[i]['pid'],
                            str(e))
                done_pid = self.child_processes[i]['pid']
                pass
            if done_pid > 0:
                self.logger.warn("Child %d exited: %d %d", i, done_pid, exit_status)
                new_pid = self.child_processes[i]['class'](id=str(i)).run()
                self.child_processes[i]['pid']=new_pid
                return
            
    def setSignal(self):
        signal.signal(signal.SIGINT, lambda(s,f):self.killChildProcesses(s,f))
        signal.signal(signal.SIGTERM, lambda(s,f):self.killChildProcesses(s,f))
        signal.signal(signal.SIGCHLD, lambda(s,f):self.restartChildProcess(s,f))
