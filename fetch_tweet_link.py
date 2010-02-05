#!/usr/bin/python

import md5
import twitter
import re
import uuid
import xmlrpclib
import sys
from optparse import OptionParser

username = "scrshot"
password = "password"

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

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    url_pattern = re.compile('((http|ftp|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)')
    scrshot_service = xmlrpclib.ServerProxy('http://localhost:8000', allow_none = True)

    api = twitter.Api(username=username, password=password)
    if options.since:
        print "Since: ", options.since
        statuses = api.GetFriendsTimeline(username, count=options.count, since_id=options.since)
    else:
        statuses = api.GetFriendsTimeline(username, count=options.count)
    for s in statuses:
        matches = re.findall(url_pattern,s.text)
        if matches:
            print s.id, " ", s.created_at, " ", s.text
            for m in matches:
                id = str(uuid.uuid1())
                task = scrshot_service.ScreenShot(m[0], id, None)
                print "Task scheduled: ", task['id'], " ", task['url'], " ", task['filename']
                
    if statuses:
        print statuses[0].id
    
