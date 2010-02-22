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

l = Link(url="http://g.cn/")
l.save()

lr = LinkRate(link=l)
lr.save()

lrs = LinkRate.objects.extra(select={'published':"SELECT COUNT(*) FROM lts_shotpublish WHERE lts_shotpublish.link_id=lts_linkrate.link_id"}, where=["published=1"])

for lr in lrs:
    print lr.published

#lrs = Link.objects.raw('SELECT lr.id as id, lr.link_id as id, lr.rate as rate, lr.rating_time as ratingtime, COUNT(sp.id) as sp_count FROM lts_linkrate as lr, lts_shotpublish as sp WHERE sp_count=0')

#for lr in lrs:
#    print lr.link.url


