# migrated from original shot_service.py

import signal, logging

from django.core.management.base import BaseCommand
from django.conf import settings
from config import Config

from lts import shot_service, url_processor, rt_shot, task_gc
from lts.process_manager import ProcessManager

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
        
        pm = ProcessManager(cfg, logger)
        shot_service.logger = logger
        shot_service.cfg = cfg
        url_processor.logger = logger
        url_processor.cfg = cfg
        rt_shot.logger = logger
        rt_shot.cfg = cfg

        for i in range(cfg.shot_service.workers):
            pm.add(shot_service.ShotProcessWorker(cfg, logger, id=("Shot%d" % i)))

        pm.add(url_processor.URLProcessWorker(cfg, logger, id='URLProcessor'))
        pm.add(rt_shot.RTShotWorker(cfg, logger, 'RTShot'))
        pm.add(task_gc.GCWorker(cfg, logger, 'TaskGC'))

        pm.startAll()
        pm.setSignal()
        
        while True:
            signal.pause()
