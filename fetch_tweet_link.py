#!/usr/bin/python

from __future__ import with_statement

import md5
import twitter
import re
import uuid
import sys
import pickle
import memcache

from optparse import OptionParser
from stompy.simple import Client

if __name__ == '__main__':
    description = '''Fetch Twitter timeline and enqueue links.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-s", "--since", dest="since", type="int",
                      help="Fetch updates after tweet id. Default for last 20 tweets.",
                      metavar="SINCE")
    parser.add_option("-c", "--count", dest="count", type="int", default=20,
                      help="Fetch at most COUNT tweets [default: %default].",
                      metavar="COUNT")

    parser.add_option("-f", "--since-file", dest="since_file", type="string",
                      default="/var/run/fetch_tweet_link.since",
                      help="Status ID file to read/write [default: %default].",
                      metavar="SINCE_FILE")

    parser.add_option("-u", "--username", dest="username", type="string",
                      default="username",
                      help="Twitter username [default: %default].",
                      metavar="USERNAME")

    parser.add_option("-p", "--password", dest="password", type="string",
                      default="password",
                      help="Twitter password [default: %default].",
                      metavar="PASSWORD")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    url_pattern = re.compile('((http|ftp|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)')
    stomp = Client()
    stomp.connect()
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    if options.since_file and ( not options.since ):
        try:
            with open(options.since_file, 'r') as f:
                try:
                    options.since=int(f.read())
                except:
                    options.since=None
        except:
            pass

    api = twitter.Api(username=options.username, password=options.password)
    if options.since:
        print "Since: ", options.since
        statuses = api.GetFriendsTimeline(options.username, count=options.count, since_id=options.since)
    else:
        statuses = api.GetFriendsTimeline(options.username, count=options.count)
    for s in statuses:
        if s.user.screen_name == options.username :
            # don't RT myself
            continue
        matches = re.findall(url_pattern,s.text)
        if matches:
            print s.id, " ", s.user.screen_name, " ", s.created_at, " ", s.text.encode('utf-8')
            for m in matches:
                id = str(uuid.uuid1())
                mc.set(id, s, time=600)
                stomp.put(pickle.dumps({'id':id,
                                        'url':m[0],
                                        'filename':None}),
                          destination="/queue/shot_source")
                
    if statuses:
        print statuses[0].id
        if options.since_file:
            try:
                with open(options.since_file, 'w') as f:
                    f.write(str(statuses[0].id))
            except:
                pass
