# migrated from original shot_service.py

import os, sys, logging, signal

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option
from config import Config, ConfigMerger

from lts import shot_service, url_processor, rt_shot, task_gc

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        )
    help = '''Screenshot service with QtPt.'''
    
    def handle(self, *args, **options):
        cfg = Config(file(settings.LTS_CONFIG))

        logger.info("Workers: %d", cfg.shot_service.workers)
        logger.info("Max width: %d", cfg.shot_service.max_width)
        logger.info("Max height: %d", cfg.shot_service.max_height)
        logger.info("Source queue: %s", cfg.queues.processed)
        logger.info("Dest queue: %s", cfg.queues.shotted)
        logger.info("Timeout: %d", cfg.shot_service.timeout)
        
        shot_service.child_processes = []
        shot_service.logger = logger
        shot_service.cfg = cfg
        url_processor.logger = logger
        url_processor.cfg = cfg
        rt_shot.logger = logger
        rt_shot.cfg = cfg

        for i in range(cfg.shot_service.workers):
            shot_service.child_processes.append(
                {'pid':shot_service.ShotProcessWorker(id=str(i)).run(),
                 'class':shot_service.ShotProcessWorker}
                )

        shot_service.child_processes.append(
            {'pid':url_processor.URLProcessWorker(id="url_processor").run(),
             'class':url_processor.URLProcessWorker
             }
            )

        shot_service.child_processes.append(
            {'pid':rt_shot.RTShotWorker(id="rt_shot").run(),
             'class':rt_shot.RTShotWorker
             }
            )

        shot_service.child_processes.append(
            {'pid':task_gc.GCWorker(id="task_gc").run(),
             'class':task_gc.GCWorker
             }
            )
        
        signal.signal(signal.SIGINT, shot_service.killChildProcesses)
        signal.signal(signal.SIGTERM, shot_service.killChildProcesses)
        signal.signal(signal.SIGCHLD, shot_service.restartChildProcess)

        while True:
            signal.pause()
