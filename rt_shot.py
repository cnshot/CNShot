#!/usr/bin/python

import stompy, pickle, memcache, sys, traceback, logging, logging.config, os, \
    twitpic, twitter, subprocess, xml, readability

from optparse import OptionParser
from config import Config, ConfigMerger
from xml.dom import minidom

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, LinkShot, Tweet

mc = None

def post_image(task, s):
    twitpic_url = None

    if cfg.rt_shot.dummy:
        logger.info("No post with dummy mode: %d %s %s",
                    s.id, str(s.user.screen_name), s.text.encode('utf-8'))
        return None

    try:
        twit = twitpic.TwitPicAPI(cfg.common.username,
                                  cfg.common.password)

        rt_text = u'RT @' + s.user.screen_name + u': ' + s.text
        logger.debug("%s", rt_text.encode('utf-8'))

        twitpic_url = twit.upload(task['filename'], 
                                  message = rt_text.encode('utf-8')[0:140],
                                  post_to_twitter=False)

        if isinstance(twitpic_url, int):
            logger.info("Failed to update image to Twitpic: %d", twitpic_url)
            twitpic_url = None
        else:
            logger.info("Uploaded %s to %s", task['id'], twitpic_url)
    except:
        logger.error("Failed to tweet image: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)
    finally:
        return twitpic_url

def update_linkshot(task, s, url):
    try:
        l = Link.objects.get(url = task['url'])
    except Link.DoesNotExist:
        logger.warn("No link object for url: %s", task['url'])
        l = None

    try:
        t = Tweet.objects.get(id=str(s.id))
        ls = LinkShot(link=l, url=url,
                      shot_time=task['shot_time'],
                      in_reply_to = t,
                      title=task['title'],
                      text=task['text'])
    except Tweet.DoesNotExist:
        ls = LinkShot(link=l, url=url,
                      shot_time=task['shot_time'],
                      title=task['title'],
                      text=task['text'])
    ls.save()

def readability_parse_file(filename, frame_url=None, task_url=None):
    logger.debug("Readability parse file: %s %s %s", filename, frame_url, task_url)
    try:
        f = file(filename)
        html_text = f.read()
        f.close()
    except IOError:
        logger.warn("Failed to open/read file: %s", filename)
        return '',''

    readability.logger = logger
    p = readability.ReadabilityProcessor(cfg)
    r = p.process(html_text, url=str(frame_url), input_charset='utf-8',
                  linkprocessor = readability.LinkProcessorUpdateURL)
    if r:
        return r['title'], r['text']
    else:
        return '',''

def readability_parse(task):
    task['title'] = ''
    task['text'] = ''

    try:
        if not task['html_filename']:
            logger.warn("No HTML file: %s", task['url'])
            return


        task['title'] = task['html_title']
        parsed_title, task['text'] = readability_parse_file(task['html_filename'],
                                                             frame_url = task['html_url'],
                                                             task_url = task['url'])

        for i in range(task['sub_frame_count']):
            filename = task['html_filename'] + str(i)
            title, text = readability_parse_file(filename,
                                                 frame_url = task['html_url' + str(i)],
                                                 task_url = task['url'])
            task['text'] += text
    except:
        logger.error("Failed to parse readability: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)

def tweet_image(task, s, url):
    if not url:
        return

    try:
        if not cfg.rt_shot.tweet:
            logger.info("Tweet disabled.")
            return

        logger.info("Tweet enalbed.")

        rt_text = u'RT @' + s.user.screen_name + u': ' + s.text
        t = unicode(url) + u" " + rt_text
        api = twitter.Api(username=cfg.common.username,
                          password=cfg.common.password)
        rts = api.PostUpdate(t[0:140], in_reply_to_status_id=s.id)

        logger.info("New tweet: %d %s %s", 
                    rts.id, str(rts.created_at),
                    rts.text.encode('utf-8'))
    except:
        logger.error("Failed to tweet image: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)

def onReceiveTask(m):
    stomp.ack(m)
    task = pickle.loads(m.body)

    if task is None:
        logger.error("Failed to parse task")
        return

    logger.info("Got task: %s %s %s", task['url'], task['filename'], task['html_filename'])

    try:
        s = mc.get(task['id'])
        mc.delete(task['id'])

        if s is None:
            # expired
            logger.error("Failed to get status of task id: %s", task['id'])
            return

        logger.info("Got tweet: %d %s %s %s",
                    s.id, str(s.user.screen_name),
                    str(s.created_at), s.text.encode('utf-8'))

        twitpic_url = post_image(task, s)

        readability_parse(task)

        update_linkshot(task, s, twitpic_url)

    finally:
        if not cfg.rt_shot.keep_file:
            try:
                if task.has_key('filename'):
                    os.unlink(task['filename'])
                if task.has_key('html_filename'):
                    os.unlink(task['html_filename'])
                    for i in range(task['sub_frame_count']):
                        os.unlink(task['html_filename']+str(i))
            except:
                pass

if __name__ == '__main__':
    description = '''RT screenshots.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-c", "--config",
                      dest="config",
                      default="lts.cfg",
                      type="string",
                      help="Config file [default %default].",
                      metavar="CONFIG")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    cfg=Config(file(filter(lambda x: os.path.isfile(x),
                           [options.config,
                            os.path.expanduser('~/.lts.cfg'),
                            '/etc/lts.cfg'])[0]))

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("rt_shot")

    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    stomp = stompy.simple.Client()
    stomp.connect()
    stomp.subscribe(cfg.queues.shotted, ack='client')

    logger.info("rt_shot started.")
    if cfg.rt_shot.dummy:
        logger.info("Dummy mode enabled.")

    while True:
        m=stomp.get(callback=onReceiveTask)

