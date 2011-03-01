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
    # avoid frequent twitter api calling on error
    schedule_job(settings.LTS_SCHEDULE['crawl'],
                 str(job.callable_name))

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
    # avoid frequent twitter api calling on error
    schedule_job(settings.LTS_SCHEDULE['tweet'],
                 str(job.callable_name))

    import tweet_shot

    cfg = Config(file(settings.LTS_CONFIG))

    tweet_shot.logger = logger
    tweet_shot.cfg = cfg

    tweet_shot.TweetShot.tweetShot()

@job_as_parameter
def cluster(job):
    # avoid frequent twitter api calling on error    
    schedule_job(settings.LTS_SCHEDULE['cluster'],
                 str(job.callable_name))

    import cluster_tweets

    cfg = Config(file(settings.LTS_CONFIG))

    cluster_tweets.logger = logger
    cluster_tweets.cfg = cfg
    
    cluster_tweets.cluster_tweets()

@job_as_parameter
def clear_cache(job):
    job.reschedule(settings.LTS_SCHEDULE['clear_cache'],
                   callable_name=str(job.callable_name))

    import cache_gc

    cfg = Config(file(settings.LTS_CONFIG))

    cache_gc.logger = logger
    cache_gc.cfg = cfg
    
    cache_gc.clear_shot_cache(cfg.cache_gc.lifetime)

@job_as_parameter
def update_twitter_accounts(job):
    # avoid frequent twitter api calling on error
    schedule_job(settings.LTS_SCHEDULE['update_twitter_accounts'],
                 str(job.callable_name))
    
    import update_twitter_users as utu

    cfg = Config(file(settings.LTS_CONFIG))

    utu.logger = logger
    utu.cfg = cfg

    utu.updateTwitterAccounts()

@job_as_parameter
def update_twitter_users(job):
    # avoid frequent twitter api calling on error
    schedule_job(settings.LTS_SCHEDULE['update_twitter_users'],
                 str(job.callable_name))
    
    import update_twitter_users as utu

    cfg = Config(file(settings.LTS_CONFIG))

    utu.logger = logger
    utu.cfg = cfg
    
    utu.updateTwitterUsers()

@job_as_parameter
def follow_users(job):
    # avoid frequent twitter api calling on error
    schedule_job(settings.LTS_SCHEDULE['follow_users'],
                   str(job.callable_name))
    
    import update_twitter_users as utu

    cfg = Config(file(settings.LTS_CONFIG))

    utu.logger = logger
    utu.cfg = cfg
    
    utu.followUsers()

@job_as_parameter
def update_tweet_mentioned(job):
    # avoid frequent twitter api calling on error
    schedule_job(settings.LTS_SCHEDULE['update_tweet_mentioned'],
                 str(job.callable_name))
    
    import update_twitter_users as utu

    cfg = Config(file(settings.LTS_CONFIG))

    utu.logger = logger
    utu.cfg = cfg
    
    utu.updateTweetMentioned()

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
        schedule_unique_job(settings.LTS_SCHEDULE['cluster'],
                            'lts_web.lts.management.commands.schedule.cluster')
        schedule_unique_job(settings.LTS_SCHEDULE['clear_cache'],
                            'lts_web.lts.management.commands.schedule.clear_cache')
        schedule_unique_job(settings.LTS_SCHEDULE['update_twitter_accounts'],
                            'lts_web.lts.management.commands.schedule.update_twitter_accounts')
        schedule_unique_job(settings.LTS_SCHEDULE['update_twitter_users'],
                            'lts_web.lts.management.commands.schedule.update_twitter_users')
        schedule_unique_job(settings.LTS_SCHEDULE['follow_users'],
                            'lts_web.lts.management.commands.schedule.follow_users')
        schedule_unique_job(settings.LTS_SCHEDULE['update_tweet_mentioned'],
                            'lts_web.lts.management.commands.schedule.update_tweet_mentioned')
