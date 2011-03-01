import os, sys, logging, threading

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django_future import schedule_job, job_as_parameter
from optparse import make_option
from config import Config, ConfigMerger

logger = logging.getLogger(__name__)

@job_as_parameter
def crawl(job):
    job.reschedule(settings.LTS_SCHEDULE['crawl'],
                   callable_name='lts_web.lts.management.commands.schedule.crawl')

    import fetch_tweet_link

    cfg = Config(file(settings.LTS_CONFIG))
    reload(sys)
    sys.setdefaultencoding('utf-8')

    fetch_tweet_link.logger = logger
    fetch_tweet_link.cfg = cfg

    fetcher = fetch_tweet_link.TweetLinkFetcher()
    fetcher.fetchTweetLinkAll()

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ()
    help = '''Schedule interval tasks.'''

    def handle(self, *args, **options):
        schedule_job(settings.LTS_SCHEDULE['crawl'],
                     'lts_web.lts.management.commands.schedule.crawl')
