import os, sys, logging, threading

from django.core.management.base import LabelCommand, CommandError
from django.conf import settings
from django_future import schedule_job, job_as_parameter
from django_future.models import ScheduledJob
from optparse import make_option
from config import Config, ConfigMerger

logger = logging.getLogger(__name__)

class ScheduledFunc:
    def __init__(self, name, model, official_reschedule):
        self.schedule_name = name
        self.model = model
        self.official_reschedule = official_reschedule

    def __call__(self, job):
        if self.schedule_name:
            if self.official_reschedule:
                job.reschedule(settings.LTS_SCHEDULE[self.schedule_name],
                               callable_name=str(job.callable_name))
            else:
                schedule_job(settings.LTS_SCHEDULE[self.schedule_name],
                             str(job.callable_name))

        cfg = Config(file(settings.LTS_CONFIG))

        self.model.run(cfg, logger)

thismodule = sys.modules[__name__]

def build_command_pair(name, model, official_reschedule):
    f = job_as_parameter(ScheduledFunc(name, model, official_reschedule))
    setattr(thismodule, name, f)
    return {
        'command': model,
        'job': f,
        }

from lts import fetch_tweet_link, image_upload, link_rating, blog_post, \
    tweet_shot, cluster_tweets, cache_gc
from lts import update_twitter_users as utu

command_list = {
    'crawl': build_command_pair('crawl', fetch_tweet_link, False),
    'img_upload': build_command_pair('img_upload', image_upload, True),
    'rating': build_command_pair('rating', link_rating, False),
    'blog': build_command_pair('blog', blog_post, False),
    'tweet': build_command_pair('tweet', tweet_shot, False),
    'cluster': build_command_pair('cluster', cluster_tweets, False),
    'clear_cache': build_command_pair('clear_cache', cache_gc, True),
    'update_twitter_accounts':
        build_command_pair('update_twitter_accounts',
                           utu.UpdateTwitterAccounts,
                           False),
    'update_twitter_users': 
        build_command_pair('update_twitter_users',
                           utu.UpdateTwitterUsers,
                           False),
    'follow_users':
        build_command_pair('follow_users',
                           utu.FollowUsers,
                           False),
    'update_tweet_mentioned':
        build_command_pair('update_tweet_mentioned',
                           utu.updateTweetMentioned,
                           False),
    }
            
def schedule_unique_job(date, callable_name, content_object=None, expires='7d',
                        args=(), kwargs={}):
    ScheduledJob.objects.filter(status='scheduled', 
                                callable_name=callable_name).delete()
    schedule_job(date, callable_name, content_object=content_object,
                 expires=expires, args=args, kwargs=kwargs)

class Command(LabelCommand):
    option_list = LabelCommand.option_list + ()
    help = '''Schedule interval tasks.'''
    args = '''<command>'''

    def handle_label(self, command, **options):
        if command == 'schedule':
            for k in command_list.keys():
                job_str = "%s.%s" % (__name__,k)
                schedule_unique_job(settings.LTS_SCHEDULE[k], job_str)
        elif command in command_list.keys():
            cfg = Config(file(settings.LTS_CONFIG))
            command_list[command]['command'].run(cfg, logger)
