#!/usr/bin/python

import xmlrpclib
import sys

s = xmlrpclib.ServerProxy('http://localhost:8000', allow_none = True)
task = s.ScreenShot(sys.argv[1], None, None)

print "Task scheduled: ", task['id'], " ", task['url'], " ", task['filename']
