import os, sys, logging, threading

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django_future import schedule_job, job_as_parameter
from django_future.models import ScheduledJob
from optparse import make_option
from config import Config, ConfigMerger

logger = logging.getLogger(__name__)

@job_as_parameter
def crawl(job):
    job.reschedule(settings.LTS_SCHEDULE['crawl'],
                   callable_name=str(job.callable_name))

    import fetch_tweet_link

    cfg = Config(file(settings.LTS_CONFIG))

    fetch_tweet_link.logger = logger
    fetch_tweet_link.cfg = cfg

    fetcher = fetch_tweet_link.TweetLinkFetcher()
    fetcher.fetchTweetLinkAll()

@job_as_parameter
def img_upload(job):
    job.reschedule(settings.LTS_SCHEDULE['img_upload'],
                   callable_name=str(job.callable_name))
    
    import image_upload

    cfg = Config(file(settings.LTS_CONFIG))

    image_upload.logger = logger
    image_upload.cfg = cfg

    image_upload.ImageUpload.uploadImages()

@job_as_parameter
def tweet(job):
    job.reschedule(settings.LTS_SCHEDULE['tweet'],
                   callable_name=str(job.callable_name))

    import tweet_shot

    cfg = Config(file(settings.LTS_CONFIG))

    tweet_shot.logger = logger
    tweet_shot.cfg = cfg

    tweet_shot.TweetShot.tweetShot()

def schedule_unique_job(date, callable_name, content_object=None, expires='7d',
                        args=(), kwargs={}):
    ScheduledJob.objects.filter(status='scheduled', 
                                callable_name=callable_name).delete()
    schedule_job(date, callable_name, content_object=content_object,
                 expires=expires, args=args, kwargs=kwargs)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ()
    help = '''Schedule interval tasks.'''

    def handle(self, *args, **options):
        schedule_unique_job(settings.LTS_SCHEDULE['crawl'],
                            'lts_web.lts.management.commands.schedule.crawl')
        schedule_unique_job(settings.LTS_SCHEDULE['img_upload'],
                            'lts_web.lts.management.commands.schedule.img_upload')
        schedule_unique_job(settings.LTS_SCHEDULE['tweet'],
                            'lts_web.lts.management.commands.schedule.tweet')
        
