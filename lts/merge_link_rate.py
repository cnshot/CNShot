#!/usr/bin/python

from lts.models import Link, Tweet, LinkRateSum

from datetime import datetime, timedelta

def getFirstTweet(link):
    ls = link.getRoot().getAliases()
    first_tweet = None
    first_t = datetime.utcnow() + timedelta(days = 1)
    for l in ls:
        try:
            tweet = Tweet.objects.filter(links=l).order_by('created_at')[0]
            if tweet.created_at < first_t:
                first_tweet = tweet
                first_t = tweet.created_at
        except IndexError:
            print("Failed to get the first tweet of link: [%d] %s"% (l.id, l))
            pass
    return first_tweet

org_ls = Link.objects.filter(alias_of = None)

for ol in org_ls:
    print("Getting link %d: %s" % (ol.id, ol.url))
    s = ol.getRateSum()
    t = getFirstTweet(ol)
    lrs = LinkRateSum(link = ol, rate = s, tweet = t)
    lrs.save()
    print("Updated link %s: %d" % (ol.url, s))
