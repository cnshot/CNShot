#!/usr/bin/python

import stompy, pickle, memcache, sys, traceback, logging, logging.config, os
import twitpic, twitter

from optparse import OptionParser

mc = None

def onReceiveTask(m):
    stomp.ack(m)
    task = pickle.loads(m.body)

    if task is None:
        logger.error("Failed to parse task")
        return

    logger.info("Got task: %s %s", task['url'], task['filename'])

    try:
        s = mc.get(task['id'])
        mc.delete(task['id'])

        if s is None:
            # expired
            logger.error("Failed to get status of task id: %d", task['id'])
            return

        logger.info("Got tweet: %d %s %s %s",
                    s.id, str(s.user.screen_name),
                    str(s.created_at), s.text.encode('utf-8'))

        if options.dummy:
            logger.info("No post with dummy mode: %i %s %s",
                        s.id, str(s.user.screen_name), s.text.encode('utf-8'))
            return

        try:
            twit = twitpic.TwitPicAPI(options.username, options.password)

            rt_text = u'RT @' + s.user.screen_name + u': ' + s.text
            logger.debug("%s", rt_text.encode('utf-8'))

            twitpic_url = twit.upload(task['filename'], 
                                      message = rt_text.encode('utf-8')[0:140],
                                      post_to_twitter=False)

            if not options.tweet:
                logger.info("Tweet disabled.")
                return
            
            logger.info("Tweet enalbed.")

            t = unicode(twitpic_url) + u" " + rt_text
            api = twitter.Api(username=options.username, password=options.password)
            rts = api.PostUpdate(t[0:140], in_reply_to_status_id=s.id)

            logger.info("New tweet: %d %s %s", 
                        rts.id, str(rts.created_at),
                        rts.text.encode('utf-8'))
        except:
            logger.error("Failed to tweet image: %s", sys.exc_info()[0])
            logger.error('-'*60)
            logger.error("%s", traceback.format_exc())
            logger.error('-'*60)
    finally:
        if not options.keep_file:
            try:
                os.unlink(task['filename'])
            except:
                pass

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

    parser.add_option("-l", "--log-config",
                      dest="log_config", 
                      default="/etc/link_shot_tweet_log.conf",
                      type="string",
                      help="Logging config file [default: %default].",
                      metavar="LOG_CONFIG")

    parser.add_option("-d", "--dummy", action="store_true", dest="dummy", 
                      default=False)

    parser.add_option("-t", "--tweet", action="store_true", dest="tweet",
                      default=False)

    parser.add_option("-k", "--keep-file", action="store_true", dest="keep_file", 
                      default=False)

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    logging.config.fileConfig(options.log_config)
    logger = logging.getLogger("rt_shot")

    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    stomp = stompy.simple.Client()
    stomp.connect()
    stomp.subscribe(options.source_queue, ack='client')

    logger.info("rt_shot started.")
    if options.dummy:
        logger.info("Dummy mode enabled.")

    while True:
        m=stomp.get(callback=onReceiveTask)

