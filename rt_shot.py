#!/usr/bin/python

import stompy
import pickle
import memcache
import twitpic
import twitter
import sys
import traceback

from optparse import OptionParser

#username = "scrshot"
#password = "password"

mc = None

def onReceiveTask(m):
    stomp.ack(m)
    task = pickle.loads(m.body)

    if task is None:
        print "Failed to parse task"
        return

    print "Got task: ", task['url'], " ", task['filename']

    s = mc.get(task['id'])
    mc.delete(task['id'])
    
    if s is None:
        # expired
        print "Failed to get status of task id: ", task['id']
        return

    print "Got tweet: ", s.id, " ", s.user.screen_name, " ", s.created_at, " ", s.text.encode('utf-8')

    try:
        twit = twitpic.TwitPicAPI(options.username, options.password)

        rt_text = u'RT @' + s.user.screen_name + u': ' + s.text
        print rt_text.encode('utf-8')

        twitpic_url = twit.upload(task['filename'], 
                                  message = rt_text.encode('utf-8')[0:140],
                                  post_to_twitter=False)

        t = unicode(twitpic_url) + u" " + rt_text
        api = twitter.Api(username=options.username, password=options.password)
        rts = api.PostUpdate(t[0:140], in_reply_to_status_id=s.id)

        print "New tweet: ", rts.id, " ", rts.created_at, " ", rts.text.encode('utf-8')
    except:
        print "Failed to tweet image: ", sys.exc_info()[0]
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60

if __name__ == '__main__':
    description = '''RT screenshots.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-s", "--source-queue",
                      dest="source_queue", default="/queue/shot_dest",
                      type="string",
                      help="Source message queue path [default: %default].",
                      metavar="SOURCE_QUEUE")

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

    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    stomp = stompy.simple.Client()
    stomp.connect()
    stomp.subscribe(options.source_queue, ack='client')
    while True:
        m=stomp.get(callback=onReceiveTask)

