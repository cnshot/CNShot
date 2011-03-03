# migrated from url_processor.py

import os, sys, logging, logging.config, threading

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option
from config import Config, ConfigMerger

from lts import url_processor

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        )
    help = '''Shot task URL pre-processor.'''
    
    def handle(self, *args, **options):
        cfg = Config(file(settings.LTS_CONFIG))

        # walk around encoding issue
        reload(sys)
        sys.setdefaultencoding('utf-8')

        url_processor.logger = logger
        url_processor.cfg = cfg

        url_processor.process_url()
