# migrated from original shot_service.py

import signal, logging, daemon, daemon.pidlockfile

from django.core.management.base import BaseCommand
from django.conf import settings
from config import Config

from lts import shot_service, url_processor, rt_shot, task_gc
from lts.process_manager import ProcessManager

global logger
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        )
    help = '''Screenshot service with QtPt.'''
    
    def unbind_pidfile(self):
        if self.daemon_context:
            logger.debug("Unbind pidfile")
            self.daemon_context.pidfile = None
    
    def run(self):
        cfg = Config(file(settings.LTS_CONFIG))
    
        logger.info("Workers: %d", cfg.shot_service.workers)
        logger.info("Max width: %d", cfg.shot_service.max_width)
        logger.info("Max height: %d", cfg.shot_service.max_height)
        logger.info("Source queue: %s", cfg.queues.processed)
        logger.info("Dest queue: %s", cfg.queues.shotted)
        logger.info("Timeout: %d", cfg.shot_service.timeout)
        
        pm = ProcessManager(cfg, logger)
        shot_service.logger = logger
        shot_service.cfg = cfg
        url_processor.logger = logger
        url_processor.cfg = cfg
        rt_shot.logger = logger
        rt_shot.cfg = cfg
    
        post_fork = lambda: self.unbind_pidfile()
    
        for i in range(cfg.shot_service.workers):
            pm.add(shot_service.ShotProcessWorker(cfg, logger, id=("Shot%d" % i), post_fork=post_fork))
    
        pm.add(url_processor.URLProcessWorker(cfg, logger, id='URLProcessor', post_fork=post_fork))
        pm.add(rt_shot.RTShotWorker(cfg, logger, 'RTShot', post_fork=post_fork))
        pm.add(task_gc.GCWorker(cfg, logger, 'TaskGC', post_fork=post_fork))
    
        pm.startAll()
        pm.setSignal()
        
        while True:
            signal.pause()
    
    def handle(self, *args, **options):
        import sys
        self.daemon_context = None
        if settings.SHOT_DAEMON:
            pidfile = daemon.pidlockfile.PIDLockFile(settings.SHOT_DAEMON_PIDFILE)
            self.daemon_context = daemon.DaemonContext(stdout=settings.SHOT_DAEMON_STDOUT,
                                                       stderr=settings.SHOT_DAEMON_STDERR,
                                                       pidfile=pidfile)
            
            # close db connection now before entering daemon, it will be reopened later
            from django.db import connection
            connection.close()
            
            with self.daemon_context:
                # reopen log
                global logger
                import logging.config, sys
                logging.config.fileConfig(settings.LOGGING_CONFIG)
                # walk around encoding issue
                reload(sys)
                sys.setdefaultencoding('utf-8') #@UndefinedVariable
                logger = logging.getLogger(__name__)
                
                self.run()                
        else:
            logger.info(__name__)
            self.run()