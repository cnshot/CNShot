# migrated from fetch_tweet_link.py

import os, sys, logging, threading

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option
from config import Config, ConfigMerger

from lts import fetch_tweet_link

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-s", "--since", dest="since", type="int",
                    help="Fetch updates after tweet id. Default for last 20 tweets.",
                    metavar="SINCE"),
        )
    help = '''Fetch Twitter timeline and enqueue links.'''
    
    def handle(self, *args, **options):
        cfg = Config(file(settings.LTS_CONFIG))

        # walk around encoding issue
        reload(sys)
        sys.setdefaultencoding('utf-8')

        if(cfg.fetch_tweet_link.lifetime):
            threading.Timer(cfg.fetch_tweet_link.lifetime, os._exit, [1]).start()

        fetch_tweet_link.logger = logger
        fetch_tweet_link.cfg = cfg

        fetcher = fetch_tweet_link.TweetLinkFetcher()
        fetcher.fetchTweetLinkAll()
        os._exit(0)

