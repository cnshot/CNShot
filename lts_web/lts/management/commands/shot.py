# migrated from original shot_service.py

import os, sys, logging, signal

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option
from config import Config, ConfigMerger

import shot_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        )
    help = '''Screenshot service with QtPt.'''
    
    def handle(self, *args, **options):
        cfg = Config(file(settings.LTS_CONFIG))

        # walk around encoding issue
        reload(sys)
        sys.setdefaultencoding('utf-8')

        logger.info("Workers: %d", cfg.shot_service.workers)
        logger.info("Max width: %d", cfg.shot_service.max_width)
        logger.info("Max height: %d", cfg.shot_service.max_height)
        logger.info("Source queue: %s", cfg.queues.processed)
        logger.info("Dest queue: %s", cfg.queues.shotted)
        logger.info("Timeout: %d", cfg.shot_service.timeout)
        
        shot_service.child_processes = []
        shot_service.logger = logger
        shot_service.cfg = cfg

        for i in range(cfg.shot_service.workers):
            pid = shot_service.ShotProcessWorker(id=str(i)).run()
            shot_service.child_processes.append(
                {'pid':pid, 'class':shot_service.ShotProcessWorker}
            )

        signal.signal(signal.SIGINT, shot_service.killChildProcesses)
        signal.signal(signal.SIGTERM, shot_service.killChildProcesses)
        signal.signal(signal.SIGCHLD, shot_service.restartChildProcess)

        while True:
            signal.pause()
