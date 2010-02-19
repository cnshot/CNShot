#!/usr/bin/python

import stompy, sys, traceback, logging, logging.config, os
import twitter, sqlite3

from Queue import Queue
from threading import Thread

class LinkRatingThread(Thread):
    def __init__(self, id):
        Thread.__init__(self)
        self.id = id

    def run(self):
        logger.info("Link rating thread %d started.", self.id)

        while not input_queue.empty():
            try:
                task = input_queue.get(block=False)
            except Thread.Empty:
                break

            # rate task
            # enqueue output queue

        # No more task available, exit

def loadTasks():
    conn = sqlite3.connect(db_filename)
    try:
        c = conn.cursor()

        c.execut("""
SELECT t.id,
       (SELECT COUNT(lr.tweet) AS lt FROM link_rate AS lr
        WHERE lr.tweet=t.id GROUP by lr.tweet ) as rc
       FROM tweet AS t, tweet_shot AS ts
       WHERE t.id = ts.tweet AND
             tweet.post_time > SOMETIME AND
             (rc IS NULL OR rc <= 0)
                 """)
        tweets = c.fetchall()

        c.execute("""
SELECT * FROM tweet, tweet_shot, tweet_rate
    WHERE tweet.id = tweet_shot.tweet AND
          tweet.id = tweet_rate.id AND
          tweet.post_time > SOMETIME AND
          tweet_rating.update_time < SOMETIME
                  """)

        tweets += c.fetchall()

        for t in tweets:
            input_queue.put(t)

    finally:
        conn.close()

if __name__ == '__main__':
    description = '''Link rating processor.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-s", "--source-queue",
                      dest="source_queue", default="/queue/url_processor",
                      type="string",
                      help="Source message queue path [default: %default].",
                      metavar="SOURCE_QUEUE")

    parser.add_option("-d", "--dest-queue", 
                      dest="dest_queue", default="/queue/shot_dest",
                      type="string",
                      help="Dest message queue path [default: %default].",
                      metavar="DEST_QUEUE")

    parser.add_option("--timeout", 
                      dest="timeout", default=20, type="int",
                      help="Timeout of HTTP request in second [default: %default].",
                      metavar="TIMEOUT")

    parser.add_option("-n", "--workers", 
                      dest="workers", default=8, type="int",
                      help="Number or worker threads [default: %default].",
                      metavar="WORKERS")

    parser.add_option("-l", "--log-config",
                      dest="log_config", 
                      default="/etc/link_shot_tweet_log.conf",
                      type="string",
                      help="Logging config file [default: %default].",
                      metavar="LOG_CONFIG")

    parser.add_option("--running-db",
                      dest="running_db", default="running.sqlite",
                      type="string",
                      help="Running DB file [default: %default].",
                      metavar="RUNNING_DB")

    # read recent tweet links from DB
    #   filter out: a) tweeted links, b) links rated in last x mins

    # feed links to input queue
    # start rating threads
    # wait for rating threads exit
    pass