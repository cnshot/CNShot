#!/usr/bin/python

import sys, os
import signal, time, logging, logging.config, threading, stompy, pickle
import unittest

from Queue import Queue
from datetime import datetime, timedelta

d = os.path.dirname(__file__)
if d == '':
   d = '.' 
sys.path.append(d + '/../')
sys.path.append(d + '/../lts_web')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, Tweet, LinkShot, LinkRate

import link_rating, tweet_shot

class DummyOptions(object):
    pass

class LinkRatingTest(unittest.TestCase):
    def setUp(self):
        self.options = DummyOptions()

        self.options.timeout = 20
        self.options.ranking_time = 7200
        self.options.max_ranking_tweets = 100

        self.queue = Queue()

        Link.objects.all().delete()
        Tweet.objects.all().delete()
        LinkShot.objects.all().delete()
        LinkRate.objects.all().delete()

        l = Link(url="http://g.cn", alias_of = None)
        l.save()

        t = Tweet(id=0,
                  text="test", 
                  created_at=datetime.utcnow() - timedelta(minutes=30))
        t.links = [l]
        t.save()

        ls = LinkShot(link=l,
                      url="http://twitpic.com/xxx",
                      shot_time=datetime.utcnow() - timedelta(minutes=15))
        ls.save()
        
        logging.basicConfig(level=logging.DEBUG)

    def tearDown(self):
        Link.objects.all().delete()
        Tweet.objects.all().delete()
        LinkShot.objects.all().delete()
        LinkRate.objects.all().delete()

    def test_link_rating(self):
        self.assertEqual(Tweet.objects.all().count(),1)
        t = Tweet.objects.all()[0]
        self.assertEqual(t.links.all().count(),1)
        l = t.links.all()[0]
        self.assertEqual(LinkShot.objects.filter(link=l).count(),1)

        q = Queue()

        link_rating.options = self.options
        link_rating.logger = logging

        link_rating.TaskProcessor.loadTasks(q)
        self.assertEqual(q.qsize(), 1)

        w = link_rating.LinkRatingThread('1', q)
        w.start()
        w.join()

        self.assertEqual(q.qsize(), 0)
        self.assertEqual(len(LinkRate.objects.filter(link=l)), 1)

        lr = LinkRate.objects.filter(link=l)[0]
        logging.debug("%s [%s] %d", lr.link, lr.rating_time, lr.rate)

        tweet_shot.logger = logging
        ls=tweet_shot.TweetShot.getLinks(7200, 5)
        self.assert_(len(ls)>0)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(LinkRatingTest)
    unittest.TextTestRunner(verbosity=1).run(suite)
