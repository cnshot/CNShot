# migrated from original rt_shot.py

import os, sys, logging, logging.config, memcache

from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from config import Config, ConfigMerger

import rt_shot

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-c", "--config",
                    dest="config",
                    default="lts.cfg",
                    type="string",
                    help="Config file [default %default].",
                    metavar="CONFIG"),
        )
    help = '''RT screenshots.'''

    def handle(self, *args, **options):
        cfg_file = options.get('config', 'lts.cfg')
        cfg = Config(file(filter(lambda x: os.path.isfile(x),
                                 [cfg_file,
                                  os.path.expanduser('~/.lts.cfg'),
                                  '/etc/lts.cfg'])[0]))

        # walk around encoding issue
        reload(sys)
        sys.setdefaultencoding('utf-8')

        logging.config.fileConfig(cfg.common.log_config)
        logger = logging.getLogger("content_process")

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
