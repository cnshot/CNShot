# migrated from original rt_shot.py

import os, sys, logging, memcache

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option
from config import Config, ConfigMerger

import rt_shot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        )
    help = '''RT screenshots.'''

    def handle(self, *args, **options):
        cfg = Config(file(settings.LTS_CONFIG))

        # walk around encoding issue
        reload(sys)
        sys.setdefaultencoding('utf-8')

        rt_shot.logger = logger
        rt_shot.cfg = cfg

        rt_shot.mc = memcache.Client(['127.0.0.1:11211'], debug=0)

        stomp = stompy.simple.Client()
        stomp.connect()
        stomp.subscribe(cfg.queues.shotted, ack='client')

        logger.info("rt_shot started.")
        if cfg.rt_shot.dummy:
            logger.info("Dummy mode enabled.")        

        while True:
            m = stomp.get(callback=rt_shot.onReceiveTask)
