#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest
import smtplib
import logging
from optparse import OptionParser

_SERVER    = 'server:port'
_USER      = 'user'
_PASSWORD  = 'password' 
_FROMADDR  = 'me@localhost'
_TOADDR    = 'me@localhost'

try:
    import conf
    
    _SERVER    = conf.MAIL_SERVER
    _USER      = conf.MAIL_USER
    _PASSWORD  = conf.MAIL_PASSWORD
    _FROMADDR  = conf.MAIL_FROMADDR
    _TOADDR    = conf.MAIL_TOADDR
    
except ImportError:
    pass

logging.basicConfig(filename='notifier.log', level=logging.DEBUG)

log = logging.getLogger("notifier")

console = logging.StreamHandler()
console.setLevel(logging.INFO)
log.addHandler(console)        
    
class Notifier():
    
    _server = 0
    
    def __init__(self, lib=smtplib):
        
        self._lib = lib
    
    def NotifyRaw(self, sbj, msg):
        
        log.debug("Senging message to %s...", _TOADDR)
    
        message = """\
From: %s
To: %s
Subject: %s

%s
""" % (_FROMADDR, _TOADDR, sbj, msg)
    
        self._server = self._lib.SMTP('%s' % _SERVER)
        self._server.starttls()
        self._server.login(_USER, _PASSWORD)
        self._server.sendmail(_FROMADDR, _TOADDR, message)        

        log.info("Message sent to email %s" % _TOADDR)


class testNotifier(unittest.TestCase):
    
    def setUp(self):
        pass        
        
    def runTest(self):

        from ludibrio import Mock

        with Mock() as smtplibMock:

            message = """\
From: %s
To: %s
Subject: %s

%s
""" % (_FROMADDR, _TOADDR, "hi", 'hello!')

            server = smtplibMock.SMTP(_SERVER)
            server.starttls()
            server.login(_USER, _PASSWORD)
            server.sendmail(_FROMADDR, _TOADDR, message)
        
        notif = Notifier(smtplibMock)
        
        notif.NotifyRaw('hi', 'hello!')
        
        smtplibMock.validate()


if __name__ == "__main__":


    parser = OptionParser(usage = "usage: %prog [options] subj message")    
    
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="show debug messages")
    
    (options, args) = parser.parse_args()

    
    if options.verbose:
        console.setLevel(logging.DEBUG)    
    
    if len(args) != 2:
        parser.print_help()
        exit(1)
    
    n = Notifier()

    n.NotifyRaw(args[0], args[1])
    
    
    
    
