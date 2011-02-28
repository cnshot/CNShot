# migrated from url_processor.py

import os, sys, logging, logging.config, threading

from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from config import Config, ConfigMerger

import url_processor

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-c", "--config",
                    dest="config",
                    default="lts.cfg",
                    type="string",
                    help="Config file [default %default].",
                    metavar="CONFIG"),
        )
    help = '''Shot task URL pre-processor.'''
    
    def handle(self, *args, **options):
        cfg_file = options.get('config', 'lts.cfg')
        cfg = Config(file(filter(lambda x: os.path.isfile(x),
                                 [cfg_file,
                                  os.path.expanduser('~/.lts.cfg'),
                                  '/etc/lts.cfg'])[0]))

        # walk around encoding issue
        reload(sys)
        sys.setdefaultencoding('utf-8')

        url_processor.logger = logger
        url_processor.cfg = cfg

        url_processor.process_url()
