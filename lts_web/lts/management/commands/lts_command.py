import os, sys, logging, logging.config, threading

from django.core.management.base import BaseCommand, CommandError
from config import Config, ConfigMerger

class LTSCommand(BaseCommand):
    def init(self, cfg_filepath):
        self.cfg = Config(file(filter(lambda x: os.path.isfile(x),
                                      [cfg_filepath,
                                       os.path.expanduser('~/.lts.cfg'),
                                       '/etc/lts.cfg'])[0]))

        # walk around encoding issue
        reload(sys)
        sys.setdefaultencoding('utf-8')

        logging.config.fileConfig(cfg.common.log_config)
        self.logger = logging.getLogger("url_process")

