#!/usr/bin/python

#import xmlrpclib
from stompy.simple import Client
import sys
import pickle
import uuid
import tempfile

#s = xmlrpclib.ServerProxy('http://localhost:8000', allow_none = True)
#task = s.ScreenShot(sys.argv[1], None, None)

#print "Task scheduled: ", task['id'], " ", task['url'], " ", task['filename']

stomp = Client()
stomp.connect()

filename = None
#if sys.hexversion >= 0x02060000:
#    f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
#else:
#    f = tempfile.NamedTemporaryFile(suffix='.png')
#filename = f.name
#f.close()

stomp.put(pickle.dumps({'id':str(uuid.uuid1()),
                        'url':sys.argv[1],
                        'filename':filename}),
          destination="/queue/shot_source")
