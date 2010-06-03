#!/usr/bin/python

import sys, traceback, logging, logging.config, os, time, ConfigParser

from optparse import OptionParser
from config import Config, ConfigMerger
from datetime import timedelta, datetime

from lts.models import LinkShot, ShotCache

def clear_shot_cache(lifetime):
    lss = LinkShot.objects.filter(shot_time__lt=datetime.utcnow()-timedelta(seconds=lifetime))

    for ls in lss:
        scs = ShotCache.objects.filter(linkshot = ls)
        for sc in scs:
            logger.info('Delete expired shot cache: %s', sc.linkshot.link.url)
            sc.delete()

if __name__ == '__main__':
    description = '''Shot cache GC.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-c", "--config",
                      dest="config",
                      default="lts.cfg",
                      type="string",
                      help="Config file [default %default].",
                      metavar="CONFIG")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    cfg=Config(file(filter(lambda x: os.path.isfile(x),
                           [options.config,
                            os.path.expanduser('~/.lts.cfg'),
                            '/etc/lts.cfg'])[0]))

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("cache_gc")

    clear_shot_cache(cfg.cache_gc.lifetime)
