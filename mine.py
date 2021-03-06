#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys    
import os
import re
import unittest
import threading
import logging
import time
import tempfile

from optparse import OptionParser
from datetime import datetime

 
_VERSION_ = "0.0.2"

class setupConfig():    
    
    _MINER_RULES_PARSED = {}
    
    def parseMinersAndRules(self):
                        
        for miner in self._MINERS:
                        
            rules = self._MINER_RULES
            rulesKeys = rules.keys()
            
            miner = miner.replace('*', '(.*?)')
            
            for k in rulesKeys:
                
                log.debug('searching: %s in %s', k, miner)
                
                if re.search(k, miner):
                    self._MINER_RULES_PARSED[miner] = rules[k]
                                
    def getMinerConfig(self, miner):
        
        r = self._MINER_RULES_PARSED.get(miner, {})
        log.debug("miner config: %s: %s", miner, r)
        return r
        
    
    def __init__(self):
    
        log.debug("conf.py setup")
        
        try:
            import conf
            
            self._USERNAME     = conf.MINER_USERNAME
            self._PASSWORD     = conf.MINER_PASSWORD
            self._MINERS       = conf.MINER_MINERS
            self._MINER_RULES  = conf.MINER_RULES
            self._MINER_RULES_PARSED = {}
            
            log.debug("conf.py imported")
            
        except ImportError:
        
            raise RuntimeError('Please make conf.py (example: conf.py.example)')
        
        
    
 
logging.basicConfig(filename='mine.log', level=logging.DEBUG)
 
log = logging.getLogger("mine")

console = logging.StreamHandler()
console.setLevel(logging.INFO)
log.addHandler(console) 

from notifier import Notifier


if sys.version_info[0] == 3:
    from urllib import request as urllib2
else:
    import urllib2


 
class MinerInfo():
 
    _infoData = {}
    _messageToSend = ''
    _domains = []
    _notifierClass = Notifier
    _urllib2Class = urllib2
    _notifySingle = False
    _showRpm = False
    _cachePath = ''
    
    def __init__(self, domains=0, notifySingle=False, **kw):
        
        log.debug("initializing class...")
        
        if domains:
            self.SetDomains(domains)
            
        if 'showRpm' in kw:
            self._showRpm = kw['showRpm']
            
        self._notifySingle = notifySingle
        
        cachePath = kw.get('cachePath', '')
         
        if cachePath:
            self._cachePath = cachePath
        else:
            cachePath = os.path.join(tempfile.gettempdir(), 'miner-checker', 'html-cache')
            try:
                os.makedirs(cachePath)
            except OSError as oe:
                pass
            log.debug('cache path: %s', cachePath)
            self._cachePath = cachePath

    
    def SetLibraries(self, notifierClass=None, urllib2Class=None):
        
        log.debug('setting custom libraries...')
        
        if type(notifierClass) != type(None):
            self._notifierClass = notifierClass

        if type(urllib2Class) != type(None):
            self._urllib2Class = urllib2Class
    
    def SetDomains(self, domains):
        
        log.debug('setting domains: %s', str(domains))
        
        self._domains = domains
        
    def GetDomains(self):

        return self._domains
        
    
    def AddMessageToSend(self, msg):
        
        assert msg
        
        log.debug("adding some message to send... %s", msg)
        
        self._messageToSend += msg
        
    def GetMessageToSend(self):
        
        return self._messageToSend

    def SetMinerRawHtmlData(self, domain, rawData):
        
        log.debug("set custom raw html data...")
        self._infoData[domain] = {}
        self._infoData[domain]['rawHtml'] = rawData


    def RequestMinerHttp(self, domain, useCache=0):
        
        log.debug("login to %s...", domain)
        
        fileName = os.path.join(self._cachePath, '%s.html' % domain)
        
        if os.path.exists(fileName) and useCache:
            log.info("using cache file %s", fileName)
            
            f = open(fileName, 'r')
            self.SetMinerRawHtmlData(domain, f.read())
            f.close()

            return None

        theurl = 'http://%s/cgi-bin/minerStatus.cgi' % domain
        username = sc._USERNAME
        password = sc._PASSWORD		
        
        log.debug("calling self._urllib2Class.HTTPPasswordMgrWithDefaultRealm()...")
        passman = self._urllib2Class.HTTPPasswordMgrWithDefaultRealm()
        
        passman.add_password(None, theurl, username, password)
        
        authhandler = self._urllib2Class.HTTPDigestAuthHandler(passman)
        
        opener = self._urllib2Class.build_opener(authhandler)
        self._urllib2Class.install_opener(opener)
        
        try:
            pagehandle = self._urllib2Class.urlopen(theurl)

        except urllib2.URLError as e:

            log.error('failed to open %s', domain)	
            msg = 'FAILED: %s\n%s' %  (domain, str(e))
            
            self.AddMessageToSend('Failed to open... %s' % msg)
            
            return None
        
        log.debug("writing %s file...", fileName)
        
        pageData = pagehandle.read()
        
        self.SetMinerRawHtmlData(domain, pageData)

        f = open(fileName, 'wb') 
        f.write(pageData)
        f.close()

        return True

    def ParseMinerInfo(self, domain):
        
        log.debug("parsing info for %s", domain)
    
        if domain in self._infoData:
            
            data = str(self._infoData[domain]['rawHtml'])
            
            self._infoData[domain]['asicIdealHashRate'] = ''
            self._infoData[domain]['asicStatusData']	= ''
            self._infoData[domain]['asicChipTemp']		= ''
            self._infoData[domain]['asicBoardTemp']		= ''
            self._infoData[domain]['asicHashRate']		= ''
            self._infoData[domain]['asicHashRateAvg']	= ''
            self._infoData[domain]['asicHWPercent']		= ''
            self._infoData[domain]['asicTimeElapsed']	= ''
            self._infoData[domain]['asicFan1Elapsed']	= ''
            self._infoData[domain]['asicFanMax'] 		= ''
            self._infoData[domain]['asicFanMin'] 		= ''

            try:
                
                tableCut = re.search('<table id="ant_devs".*?/table>', data, re.DOTALL)
                self._infoData[domain]['asicStatusData']    = re.findall('cbi-table-1-status">(.*?)<', tableCut.group(0), re.DOTALL)                
                self._infoData[domain]['asicChipTemp']		= re.findall('<div id="cbi-table-1-temp2">(.*?)</div>', data, re.DOTALL)
                self._infoData[domain]['asicBoardTemp']		= re.findall('<div id="cbi-table-1-temp">(.*?)</div>', data, re.DOTALL)
                self._infoData[domain]['asicHashRate']		= re.search('<div id="ant_ghs5s">(.*?)</div>', data, re.DOTALL).group(1)
                self._infoData[domain]['asicHashRateAvg']	= re.search('<div id="ant_ghsav">(.*?)</div>', data, re.DOTALL).group(1)
                tmp = re.findall('<div id="cbi-table-1-diffaccepted">(.*?)</div>', data, re.DOTALL)
                tmp = tmp[-1]
                self._infoData[domain]['asicHWPercent']		= tmp
                self._infoData[domain]['asicTimeElapsed']	= re.search('<div id="ant_elapsed">(.*?)</div>', data, re.DOTALL).group(1)	
                self._infoData[domain]['asicFan1Elapsed']	= re.search('<div id="ant_elapsed">(.*?)</div>', data, re.DOTALL).group(1)

            except IndexError as e:
                msg = "Parsing error 1 on %s: %s" % (domain, e)
                
                self.AddMessageToSend(msg + '\n')

                return
            
            except AttributeError as e:
                msg = "Parsing error 2 on %s: %s" % (domain, e)
                
                self.AddMessageToSend(msg + '\n')

                return
            #
            # filter some data
            # 
            
            newChipTemp = []
            for i in self._infoData[domain]['asicChipTemp']:
                if i:
                    newChipTemp.append(i)
            self._infoData[domain]['asicChipTemp'] = newChipTemp

            newBoardTemp = []
            for i in self._infoData[domain]['asicBoardTemp']:
                if i:
                    newBoardTemp.append(i)
            self._infoData[domain]['asicBoardTemp'] = newBoardTemp

    
            idealHashRate = ''
            try:
                idealHashRate = re.findall('<div id="cbi-table-1-rate2">(.*?)</div>', data, re.DOTALL)[-1]
            except IndexError:
            
                msg = 'No ideal hash rate found' 
                log.warning(msg)

            self._infoData[domain]['asicIdealHashRate'] = idealHashRate
            
            #
            # grab min\max values
            #
            
            maxVal = 9999
            
            fanMax = 0
            fanMin = maxVal
            for val in re.findall('<td id="ant_fan.*?>(.*?)</td>', data, re.DOTALL):
                v = int(val.replace(',', ''))
                if v:
                    if v > fanMax:          
                        fanMax = v
                    if v < fanMin:
                        fanMin = v
            
            assert fanMax
            assert fanMin != maxVal
            
            self._infoData[domain]['asicFanMaxRpm'] = fanMax
            self._infoData[domain]['asicFanMinRpm'] = fanMin
            
            #
            # calculate percentage
            #
            
            percentMaxVal = 5880
            
            fanMax = 100 * fanMax / percentMaxVal
            fanMin = 100 * fanMin / percentMaxVal
            
            self._infoData[domain]['asicFanMax'] = '%d' % int(fanMax)
            self._infoData[domain]['asicFanMin'] = '%d' % int(fanMin)
            

    def IsStatusOk(self, status):
    
        log.debug("IsStatusOk(%s)", status)
    
        assert(type(status) == list)

        c = 0
        for sym in ' '.join(status):
            if sym == 'x':
                c += 1
                
        if c:
            return '!%d' % c
        else:
            return 'OK'


    def CheckMinerHashRate(self, domain):
        '''
            If real hashrate lower than ideal hashrate - 10%, then it supposed to be error... 
        '''

        assert self._infoData[domain] 
        
        domainDict = self._infoData[domain]
        
        currentHashRate = domainDict['asicHashRate'][:-3].replace(',', '').replace('.', '')
        currentHashRateInt = int(currentHashRate)
        
        if not domainDict['asicIdealHashRate']:
            log.warning('can\'t calculate "normal" hashrate because ideal hashrate is missing')
            return
        
        idealHashRate = domainDict['asicIdealHashRate'][:-3].replace(',', '').replace('.', '')
        idealHashRateInt = int(idealHashRate)
        
        delta = idealHashRateInt - currentHashRateInt
        ideal10 = idealHashRateInt * 0.30
        
        log.debug("%s hashrate: ideal %s, current %s", domain, currentHashRate, idealHashRate)
        
        if delta > ideal10:
            
            log.error('miner %s hashrate is to low (%s < %s - 30 percent)', domain,
                             currentHashRate, idealHashRate)
            
            raise ValueError('miner %s hashrate is to low (%s < %s - 10 percent)' % (domain,
                             currentHashRate, idealHashRate))

        
    def CheckMinerTemp(self, domain):
        
        assert self._infoData[domain] 
        domainDict = self._infoData[domain]
        
        log.debug("CheckMinerTemp() %s", str(domainDict['asicChipTemp']))
        
        if not domainDict['asicChipTemp']:
            log.warning("can't check miner temp because chip temp is missing")
            return
       

	
	 
        maxTemp = 0
        for temp in domainDict['asicChipTemp']:

            if temp == '-':
                temp = '0'
	

            if int(temp) > maxTemp:
                maxTemp = int(temp) 
                
        log.debug("%s fan speed percent: current %d, max = %s", domain, maxTemp, domainDict['asicFanMax'])
        
        maxTempInConfig = sc.getMinerConfig(domain).get('maxTemp', 0)
        
        if maxTempInConfig:
             
                
            if maxTemp > sc.getMinerConfig(domain)['maxTemp']: # you can also int(domainDict['asicFanMax']) for example
                raise ValueError('miner %s high temp reached (temp = %d, max fan rpm = %s)' %
                                (domain, maxTemp, domainDict['asicFanMax']))


    def MakeMinerInfoDigest(self, domain):
    
        out = ''
            
        if domain in self._infoData:

            out += '%s:  ' % (domain)
            
            if self._infoData[domain]['asicIdealHashRate']:
                
                out += '%s (%s) [%09s]  ' % (self._infoData[domain]['asicHashRate'],
                    self._infoData[domain]['asicHashRateAvg'],
                    self._infoData[domain]['asicIdealHashRate'])
            else:
                out += '%s (%s)  ' % (self._infoData[domain]['asicHashRate'],
                    self._infoData[domain]['asicHashRateAvg'])
                
            out += '%s  ' % self._infoData[domain]['asicHWPercent']
            out += '%10s  ' % self._infoData[domain]['asicTimeElapsed']
            out += '%05s  ' % self.IsStatusOk(self._infoData[domain]['asicStatusData'])
            
            if self._infoData[domain]['asicChipTemp']:
                out += '%-12s  ' % ' '.join((self._infoData[domain]['asicChipTemp']))
            else:
                out += '%-12s  ' % ' '.join((self._infoData[domain]['asicBoardTemp']))

            if self._showRpm:
                out += '%s|%s  ' % (self._infoData[domain]['asicFanMaxRpm'], 
                    self._infoData[domain]['asicFanMinRpm'])

            else:    
                out += '%s|%s  ' % (self._infoData[domain]['asicFanMax'] + '%', 
                    self._infoData[domain]['asicFanMin'] + '%')
            
            out += '\n'
        
        log.debug("digest for %s: %s", domain, out)
        
        return out

    def MakeAllInfo(self):
        
        log.debug("making all info")
        
        out = ''
        
        for dom in self.GetDomains():
        
            if self.RequestMinerHttp(dom, useCache=0):
                        
                self.ParseMinerInfo(dom)
                
                s = self.MakeMinerInfoDigest(dom)
                out += s
                
                try:
                    self.CheckMinerHashRate(dom)
                except ValueError as v:
                    self.AddMessageToSend(str(v) + '\n')
                    
                try:
                    self.CheckMinerTemp(dom)
                except ValueError as v:
                    self.AddMessageToSend(str(v) + '\n')
            
        
        return out
        
    def Info(self):
                        
        allInfo = self.MakeAllInfo()
        
        if self._notifySingle:
        
            msg = self.GetMessageToSend()
            if msg:
                
                log.debug("callig .NotifyRaw: %s, %s", 'Some error with miners', msg + '\n' + allInfo)
                self._notifierClass().NotifyRaw('Some error with miners', msg + '\n' + allInfo)
                        
        log.info("info: %s", allInfo)
        
        return allInfo

class MinerInfoThread(threading.Thread):
    
    _domain = ''
    _minerInfo = None
    _data = ''
    _dataToSend = ''
    
    def __init__(self, domain, notifierClass=None, urllib2Class=None, **kw):
        threading.Thread.__init__(self)
        self._domain = domain    
        self._minerInfo = MinerInfo([self._domain], **kw)
        self._minerInfo.SetLibraries(notifierClass, urllib2Class)
                
        log.debug("miner thread created for domain %s", domain)
            
    def run(self):
        
        
        log.debug("running thread for domain %s...", self._domain)
        self._data = self._minerInfo.MakeAllInfo()
        self._dataToSend = self._minerInfo.GetMessageToSend()
        
    def GetInfo(self):
        
        return self._data, self._dataToSend

class MinerInfoMultithreaded():
    
    _threads = []
    _infoData = ''
    _dataToSend = ''
    
    def __init__(self, miners, notifierClasses=None, urllib2Classes=None, **kw):
        
        self._threads = []
        
        for i in range(0, len(miners)):
            
            notifierClass = None
            urllib2Class = None
             
            if notifierClasses:
                notifierClass = notifierClasses[i]
                 
            if urllib2Classes:
                urllib2Class = urllib2Classes[i]
                
            domain = miners[i]
            
            thread = MinerInfoThread(domain, notifierClass=notifierClass, urllib2Class=urllib2Class, **kw)
            
            self._threads.append(thread)

        log.debug("created multithreaded object [thread count = %d]", len(self._threads))            
            
    def MakeAllInfoMulti(self):
        
        log.debug("running all threads [%d]", len(self._threads))
        
        for thread in self._threads:
            thread.start()
            
        log.debug("joining all threads [%d]", len(self._threads))
        
        for thread in self._threads:
            thread.join()
            d, dT = thread.GetInfo()
            
            self._infoData += d
            self._dataToSend += dT   
        
        self._threads = []
        
        log.debug("multithreaded data gathered")
        
        return self._infoData, self._dataToSend

class testMiner(unittest.TestCase):
    
    def setUp(self):
        pass        
        
    def runTest(self):
        
        console.setLevel(logging.DEBUG)
        
        log.info("running self-tests")
         
        log.debug("running test: IsStatusOk test")
        
        global sc
        sc = setupConfig()
         
        mInfo = MinerInfo()
         
        status = mInfo.IsStatusOk(['oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo ooooooo',
                                   'oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo ooooooo',
                                   'oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo ooooooo'])
        self.assertEqual("OK", status, "test should be OK")
 
        status = mInfo.IsStatusOk(['oooooooo oooooooo oooooooo oooooooo oooooooo oooxoooo oooooooo ooooooo',
                                   'oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo ooooooo',
                                   'oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo ooooooo'])
        self.assertEqual("!1", status, "test should find one error")
 
        status = mInfo.IsStatusOk(['oxoooooo oooxoooo ooxooooo oooooxoo ooooooxo oooxoooo oxooxooo oxooxoo'])
        self.assertEqual("!10", status, "test should find ten errors")
         
                  
        log.info("running test: OK test")
         
        mInfo = MinerInfo()
        
        f = open(os.path.join('test-data', 'testOk.html'), 'r')
        dat = f.read()
        f.close()
         
        mInfo.SetMinerRawHtmlData('domain', dat)
        mInfo.ParseMinerInfo('domain')
        s = mInfo.MakeMinerInfoDigest('domain')
        s1 = 'domain:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69%|67%  \n'
         
        self.assertEqual(s1, s, 'parse from test-data test')
         
        mInfo.CheckMinerHashRate('domain')
        mInfo.CheckMinerTemp('domain')
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
         
        log.info("running test: low hashrate test")
         
        mInfo = MinerInfo()
        
        f = open(os.path.join('test-data', 'lowHashRate.html'), 'r')
        dat = f.read()
        f.close()
         
        mInfo.SetMinerRawHtmlData('domain', dat)
        mInfo.ParseMinerInfo('domain')
         
        msg = ''
         
        try:
            mInfo.CheckMinerHashRate('domain')
        except ValueError as v:
            msg = v
         
        self.assertTrue(msg, 'low hashrate test')
         
        mInfo.CheckMinerTemp('domain')
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
         
        log.info("running test: high temp test")
 
        mInfo = MinerInfo()
        
        f = open(os.path.join('test-data', 'highTemp.html'), 'r')
        dat = f.read()
        f.close()
        mInfo.SetMinerRawHtmlData('domain', dat)
        mInfo.ParseMinerInfo('domain')
         
        msg = ''
         
        try:
            mInfo.CheckMinerTemp('domain')
        except ValueError as v:
            msg = v
         
        self.assertTrue(msg, 'too high temp test')
         
        mInfo.CheckMinerHashRate('domain')
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
         

        log.info("running test: Parse error 1")
         
        mInfo = MinerInfo()

        f = open(os.path.join('test-data', 'parseError.html'), 'r')
        dat = f.read()
        f.close()
         
        mInfo.SetMinerRawHtmlData('domain', dat)
         
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
        mInfo.ParseMinerInfo('domain')
        self.assertTrue(mInfo.GetMessageToSend(), "should be message")
  
        
        log.info("running test: Parse error 2")
         
        mInfo = MinerInfo()
        
        f = open(os.path.join('test-data', 'parseError2.html'), 'r')
        dat = f.read()
        f.close()
        
        mInfo.SetMinerRawHtmlData('domain', dat)
         
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
        mInfo.ParseMinerInfo('domain')
        self.assertTrue(mInfo.GetMessageToSend(), "should be message")
         
         
        log.info("running test: Parse error 3")
         
        mInfo = MinerInfo()
        
        f = open(os.path.join('test-data', 'parseError3.html'), 'r')
        dat = f.read()
        f.close()
        
        mInfo.SetMinerRawHtmlData('domain', dat)
         
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
        mInfo.ParseMinerInfo('domain')
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
         
        
        log.info("running test: Mock test for network") 
        
        if sys.version_info[0] == 3:
            
            from unittest.mock import MagicMock
            
        else:
            
            from mock import MagicMock
        
        f = open(os.path.join('test-data','testOk.html'), 'rb')
        data = f.read()
        f.close()
        
        urllib2Mock = MagicMock()
        pageHandleMock = MagicMock()
                
        attrs = {'urlopen.return_value': pageHandleMock,}
        urllib2Mock.configure_mock(**attrs)

        attrs = {'read.return_value': data,}
        pageHandleMock.configure_mock(**attrs)
         
        mInfo = MinerInfo(['domain'])
        mInfo.SetLibraries(None, urllib2Class=urllib2Mock)
        
        s = mInfo.Info()
        
        self.assertEqual(len(pageHandleMock.mock_calls), 1)
        self.assertEqual(len(urllib2Mock.mock_calls), 7)
        self.assertEqual("domain:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69%|67%  \n", 
                 s, "urllib2 mock test")
        
        
        log.info("running test: Mock test for notifier")
        
        notifierMock = MagicMock() 
        
        f = open(os.path.join('test-data','lowHashRate.html'), 'rb')
        data = f.read()
        f.close()
        
        urllib2Mock = MagicMock()
        pageHandleMock = MagicMock()
                
        attrs = {'urlopen.return_value': pageHandleMock,}
        urllib2Mock.configure_mock(**attrs)

        attrs = {'read.return_value': data,}
        pageHandleMock.configure_mock(**attrs)
         
        mInfo = MinerInfo(['domain'], notifySingle=True)
        mInfo.SetLibraries(notifierClass=notifierMock, urllib2Class=urllib2Mock)
         
        s = mInfo.Info()
         
        self.assertEqual("domain:  11,845.93 (13,849.65) [14,004.90]  0.0007%  13d8h26m24s     OK  75 96 78      69%|65%  \n", 
                         s, "notifier mock test")    

        calls = notifierMock.mock_calls
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][0], '().NotifyRaw')
        self.assertEqual(calls[1][1], ('Some error with miners', 
                              'miner domain hashrate is to low (11845 < 14004 - 10 percent)\n\ndomain:  11,845.93 (13,849.65) [14,004.90]  0.0007%  13d8h26m24s     OK  75 96 78      69%|65%  \n'))


        log.info("running test: Mutithreaded test")

        f = open(os.path.join('test-data','testOk.html'), 'rb')
        data = f.read()
        f.close()
        
        urllib2Mock = MagicMock()
        pageHandleMock = MagicMock()
                
        attrs = {'urlopen.return_value': pageHandleMock,}
        urllib2Mock.configure_mock(**attrs)

        attrs = {'read.return_value': data,}
        pageHandleMock.configure_mock(**attrs)
        
        notifierMock = MagicMock()
        
        domains = ['domain', 'domain2']
        urllib2s = [urllib2Mock, urllib2Mock]
        notifiers = [notifierMock, notifierMock]
         
        multi = MinerInfoMultithreaded(domains, notifiers, urllib2s)
         
        d, s = multi.MakeAllInfoMulti()
        
        textResult = """domain:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69%|67%  
domain2:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69%|67%  
"""

        messageResult = ''
        
        self.assertEqual(d, textResult, "comparing text")
        self.assertEqual(s, messageResult, "comparing message to send text")
        
        self.assertEqual(len(urllib2Mock.mock_calls), 14)
        self.assertFalse(notifierMock.mock_calls)
        
        log.info("running test: s7 html test")
        
        f = open(os.path.join('test-data','s7.html'), 'rb')
        data = f.read()
        f.close()
        
        urllib2Mock = MagicMock()
        pageHandleMock = MagicMock()
                
        attrs = {'urlopen.return_value': pageHandleMock,}
        urllib2Mock.configure_mock(**attrs)

        attrs = {'read.return_value': data,}
        pageHandleMock.configure_mock(**attrs)
         
        mInfo = MinerInfo(['domain'])
        mInfo.SetLibraries(None, urllib2Class=urllib2Mock)
                  
        s = mInfo.MakeAllInfo()
        
        self.assertEqual('domain:  4,565.38 (4,716.19)  0.0017%  4d16h21m47s     !2  38 45 43      61%|59%  \n', s, "comparing text")        
                  
        self.assertEqual(len(pageHandleMock.mock_calls), 1)
        self.assertEqual(len(urllib2Mock.mock_calls), 7)
        self.assertEqual(mInfo.GetMessageToSend(), '')
        
        log.info("running test: s7-1 html test")
        
        f = open(os.path.join('test-data','s7-1.html'), 'rb')
        data = f.read()
        f.close()
        
        urllib2Mock = MagicMock()
        pageHandleMock = MagicMock()
                
        attrs = {'urlopen.return_value': pageHandleMock,}
        urllib2Mock.configure_mock(**attrs)

        attrs = {'read.return_value': data,}
        pageHandleMock.configure_mock(**attrs)
         
        mInfo = MinerInfo(['domain'])
        mInfo.SetLibraries(None, urllib2Class=urllib2Mock)
                  
        s = mInfo.MakeAllInfo()
        
        self.assertEqual('domain:  4,889.69 (4,717.43)  0.0018%   6d17h5m6s     OK  41 47 46      65%|63%  \n', s, "comparing text")        
                  
        self.assertEqual(len(pageHandleMock.mock_calls), 1)
        self.assertEqual(len(urllib2Mock.mock_calls), 7)        

        log.info("running test: s7-2 html test")
        
        f = open(os.path.join('test-data','s7-2.html'), 'rb')
        data = f.read()
        f.close()
        
        urllib2Mock = MagicMock()
        pageHandleMock = MagicMock()
                
        attrs = {'urlopen.return_value': pageHandleMock,}
        urllib2Mock.configure_mock(**attrs)

        attrs = {'read.return_value': data,}
        pageHandleMock.configure_mock(**attrs)
         
        mInfo = MinerInfo(['domain'])
        mInfo.SetLibraries(None, urllib2Class=urllib2Mock)
                  
        s = mInfo.MakeAllInfo()
        
        self.assertEqual('domain:  1,620.13 (1,572.64)  0.0004%  6d17h26m9s     OK  53            69%|69%  \n', s, "comparing text")        
                  
        self.assertEqual(len(pageHandleMock.mock_calls), 1)
        self.assertEqual(len(urllib2Mock.mock_calls), 7)      

        sc2 = setupConfig()
        sc2._MINERS = ['192.168.0.1']
        sc2._MINER_RULES = {'192.168.0.1': {'maxTemp': 90} }
        sc2.parseMinersAndRules()
        
        rules = sc2.getMinerConfig('192.168.0.1')
                
        self.assertEqual(rules['maxTemp'], 90)


        sc2 = setupConfig()
        sc2._MINERS = ['192.168.0.1', '192.168.0.255']
        
        isException = False
                
        try:
            sc2.getMinerConfig('192.168.0.')['maxTemp']
        except KeyError:
            isException = True
            
        self.assertTrue(isException)
                
        sc2._MINER_RULES = {'192.168.0.*': {'maxTemp': 93} }
        sc2.parseMinersAndRules()
        
        rules = sc2.getMinerConfig('192.168.0.1')
        self.assertEqual(rules['maxTemp'], 93)

        rules = sc2.getMinerConfig('192.168.0.255')
        self.assertEqual(rules['maxTemp'], 93)


        rules = sc2.getMinerConfig('192.168.1.1')
        self.assertEqual(rules, {})

        log.info('*** All tests OK ***')
        


if __name__ == "__main__":
    
    parser = OptionParser(usage = "usage: %prog [options]", version = "%prog " + _VERSION_)    
    
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="show debug messages")
    
    parser.add_option("-n", "--no-mail-notify",
                      action="store_true", dest="noNotify", default=False,
                      help="do not send any email notifications")

    parser.add_option("-f", "--auto-refresh",
                      action="store_true", dest="autoRefresh", default=False,
                      help="auto refresh data on console")

    parser.add_option("-t", "--auto-refresh-time", type="int",
                      action="store", dest="autoRefreshTime", default=3,
                      help="auto refresh time. Valid for -f option only. Default value is 3 seconds")

    parser.add_option("-r", "--show-rpm", 
                      action="store_true", dest="showRpm", default=False,
                      help="shows rpm instead of percent")

    parser.add_option("-w", "--work-path", type="string",
                      action="store", dest="workPath", default='',
                      help="change default program work path")

    parser.add_option("-c", "--cache-path", type="string",
                      action="store", dest="cachePath", default='',
                      help="change default program cache path")


    (options, args) = parser.parse_args()
           
    if options.verbose:
        console.setLevel(logging.DEBUG)    
    
    if args:
        parser.print_help()
        exit(-1)
        
    if options.workPath:
        wp = os.path.abspath(os.path.expanduser(options.workPath))
        log.debug("work path set: %s", wp)
        sys.path.append(wp)

    cachePath = options.cachePath
    if cachePath:
        cachePath = os.path.abspath(os.path.expanduser(cachePath))
        log.debug("cache path set: %s", cachePath)
            
    log.debug("call setupConfig()")
    
    global sc
    sc = setupConfig()
    sc.parseMinersAndRules()


    if options.autoRefresh:

        console.setLevel(logging.CRITICAL)

        os.system('cls' if os.name == 'nt' else 'clear')
    
        print('requestig...')
      
        while True:            
            
            multiInfo = MinerInfoMultithreaded(sc._MINERS, showRpm=options.showRpm,
                                               cachePath=options.cachePath)
         
            myData, mySend = multiInfo.MakeAllInfoMulti()
            
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print('[*] Info ' + datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"))
            print(myData)
            print('[*] Errors')
            print(mySend)
            
            time.sleep(options.autoRefreshTime)
            
    multiInfo = MinerInfoMultithreaded(sc._MINERS, showRpm=options.showRpm, cachePath=cachePath)
    
    log.info(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S, requesting..."))
         
    myData, mySend = multiInfo.MakeAllInfoMulti()
    
    log.info("%s", myData)
    
    if mySend:
        if not options.noNotify:
            Notifier().NotifyRaw("Miner errors", mySend)
        else:
            print('[!] Errors:')
            print(mySend)
    
            
 
        
