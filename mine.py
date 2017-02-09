import urllib2
import os
import re
import unittest
import threading
import logging
import time

from optparse import OptionParser
from datetime import datetime
from ludibrio import Mock 

# TODO: add GUI with Kivy
 
_VERSION_ = "0.0.2"

try:
    import conf
    
    _USERNAME   = conf.MINER_USERNAME
    _PASSWORD   = conf.MINER_PASSWORD
    _MINERS     = conf.MINER_MINERS
    
except ImportError:
    pass 
 
logging.basicConfig(filename='mine.log', level=logging.DEBUG)
 
log = logging.getLogger("mine")

console = logging.StreamHandler()
console.setLevel(logging.INFO)
log.addHandler(console) 

from notifier import Notifier
 
class MinerInfo():
 
    _infoData = {}
    _asicStatusOk = 'oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo ooooooo'
    _messageToSend = ''
    _domains = []
    _notifierClass = Notifier
    _urllib2Class = urllib2
    _notifySingle = False
    
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
        
    
    def __init__(self, domains=0, notifySingle=False):
        
        log.debug("initializing class...")
        
        if domains:
            self.SetDomains(domains)
            
        self._notifySingle = notifySingle


    def SetMinerRawHtmlData(self, domain, rawData):
        
        log.debug("set custom raw html data...")
        self._infoData[domain] = {}
        self._infoData[domain]['rawHtml'] = rawData


    def RequestMinerHttp(self, domain, useCache=0):
        
        log.info("login to %s...", domain)
        
        fileName = "html-cache/%s.html" % domain
        
        if os.path.exists(fileName) and useCache:
            log.info("using cache file %s", fileName)
            
            self.SetMinerRawHtmlData(domain, open(fileName, 'r').read())

            return None

        theurl = 'http://%s/cgi-bin/minerStatus.cgi' % domain
        username = _USERNAME
        password = _PASSWORD		
        
        log.debug("calling self._urllib2Class.HTTPPasswordMgrWithDefaultRealm()...")
        passman = self._urllib2Class.HTTPPasswordMgrWithDefaultRealm()
        
        passman.add_password(None, theurl, username, password)
        
        authhandler = self._urllib2Class.HTTPDigestAuthHandler(passman)
        
        opener = self._urllib2Class.build_opener(authhandler)
        self._urllib2Class.install_opener(opener)
        
        try:
            pagehandle = self._urllib2Class.urlopen(theurl)

        except urllib2.URLError, e:

            log.error('failed to open %s', domain)	
            msg = 'FAILED: %s\n%s' %  (domain, str(e))
            
            self.AddMessageToSend('Failed to open... %s' % msg)
            
            return None
        
        log.debug("writing %s file...", fileName)
        
        pageData = pagehandle.read()
        
        self.SetMinerRawHtmlData(domain, pageData)

        open(fileName, 'w').write(pageData)

        return True

    def ParseMinerInfo(self, domain):
        
        log.debug("parsing info for %s", domain)
    
        if self._infoData.has_key(domain):
            
            data = self._infoData[domain]['rawHtml']
            
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
                self._infoData[domain]['asicStatusData']	= re.findall('cbi-table-1-status"> (.*?)<', data, re.DOTALL)
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
                msg = "Parsing error 1 on %s: %s" % (domain, e.message)
                
                self.AddMessageToSend(msg + '\n')

                return
            
            except AttributeError as e:
                msg = "Parsing error 2 on %s: %s" % (domain, e.message)
                
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
                self.AddMessageToSend(msg + '\n')
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
            
            #
            # calculate percentage
            #
            
            percentMaxVal = 5880
            
            fanMax = 100 * fanMax / percentMaxVal
            fanMin = 100 * fanMin / percentMaxVal
            
            self._infoData[domain]['asicFanMax'] = '%d' % int(fanMax)
            self._infoData[domain]['asicFanMin'] = '%d' % int(fanMin)
            

    def IsStatusOk(self, status):
    
        o = ''
        isOk = 1
        
        for line in status:
            o += '  %s\n' % line
        
            if line != self._asicStatusOk:
                isOk = 0
        
        if isOk:
            return 'OK'
        else:
            c = 0
            for sym in o:
                if sym == 'x':
                    c += 1

            return '!%d' % c


    def CheckMinerHashRate(self, domain):
        '''
            If real hashrate lower than ideal hashrate - 10%, then it supposed to be error... 
        '''

        assert self._infoData[domain] 
        
        domainDict = self._infoData[domain]
        
        currentHashRate = domainDict['asicHashRate'][:-3].replace(',', '').replace('.', '')
        currentHashRateInt = int(currentHashRate)
        
        idealHashRate = domainDict['asicIdealHashRate'][:-3].replace(',', '').replace('.', '')
        idealHashRateInt = int(idealHashRate)
        
        delta = idealHashRateInt - currentHashRateInt
        ideal10 = idealHashRateInt * 0.10
        
        log.debug("%s hashrate: ideal %s, current %s", domain, currentHashRate, idealHashRate)
        
        if delta > ideal10:
            
            log.error('miner %s hashrate is to low (%s < %s - 10 percent)', domain,
                             currentHashRate, idealHashRate)
            
            raise ValueError('miner %s hashrate is to low (%s < %s - 10 percent)' % (domain,
                             currentHashRate, idealHashRate))

        
    def CheckMinerTemp(self, domain):
        '''
            If miner temp > 103 degrees and fan speed is more than 90%, than it is no good...
        '''

        assert self._infoData[domain] 
        domainDict = self._infoData[domain]
        
        maxTemp = 0
        for temp in domainDict['asicChipTemp']:
            if int(temp) > maxTemp:
                maxTemp = int(temp) 
                
        log.debug("%s fan speed percent: current %d, max = %s", domain, maxTemp, domainDict['asicFanMax'])
                
        if maxTemp > 103 and int(domainDict['asicFanMax']) > 90:
            raise ValueError('miner %s high temp reached (temp = %d, max fan rpm = %s)' %
                             (domain, maxTemp, domainDict['asicFanMax']))


    def MakeMinerInfoDigest(self, domain):
    
        out = ''
            
        if self._infoData.has_key(domain):

            out += '%s:  ' % (domain) 
            out += '%s (%s) [%09s]  ' % (self._infoData[domain]['asicHashRate'],
                self._infoData[domain]['asicHashRateAvg'],
                self._infoData[domain]['asicIdealHashRate'])
            out += '%s  ' % self._infoData[domain]['asicHWPercent']
            out += '%10s  ' % self._infoData[domain]['asicTimeElapsed']
            out += '%05s  ' % self.IsStatusOk(self._infoData[domain]['asicStatusData'])
            out += '%-12s  ' % ' '.join((self._infoData[domain]['asicChipTemp']))
            out += '%s|%s  ' % (self._infoData[domain]['asicFanMax'], 
                self._infoData[domain]['asicFanMin'])
            
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
                    self.AddMessageToSend(v.message + '\n')
                    
                try:
                    self.CheckMinerTemp(dom)
                except ValueError as v:
                    self.AddMessageToSend(v.message + '\n')
            
        
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
    
    def __init__(self, domain, notifierClass=None, urllib2Class=None):
        threading.Thread.__init__(self)
        self._domain = domain    
        self._minerInfo = MinerInfo([self._domain])
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
    
    def __init__(self, miners, notifierClasses=None, urllib2Classes=None):
        
        self._threads = []
        
        for i in range(0, len(miners)):
            
            notifierClass = None
            urllib2Class = None
            
            if notifierClasses:
                notifierClass = notifierClasses[i]
                
            if urllib2Classes:
                urllib2Class = urllib2Classes[i]
                
            domain = miners[i]
            
            thread = MinerInfoThread(domain, notifierClass=notifierClass, urllib2Class=urllib2Class)
            
            self._threads.append(thread)

        log.debug("created multithreaded object [thread count = %d]", len(self._threads))            
            
    def MakeAllInfo(self):
        
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
        
        log.info("running self-tests")
         
        log.debug("running test: IsStatusOk test")
         
        mInfo = MinerInfo()
         
        status = mInfo.IsStatusOk('oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo oooooooo ooooooo')
        self.assertEqual("!0", status, "test should be OK")
 
        status = mInfo.IsStatusOk('oooooooo oooooooo oooooooo oooooooo oooooooo oooxoooo oooooooo ooooooo')
        self.assertEqual("!1", status, "test should find one error")
 
        status = mInfo.IsStatusOk('oxoooooo oooxoooo ooxooooo oooooxoo ooooooxo oooxoooo oxooxooo oxooxoo')
        self.assertEqual("!10", status, "test should find ten errors")
         
                  
        log.info("running test: OK test")
         
        mInfo = MinerInfo()
         
        mInfo.SetMinerRawHtmlData('domain', open('test-data/testOk.html', 'r').read())
        mInfo.ParseMinerInfo('domain')
        s = mInfo.MakeMinerInfoDigest('domain')
        s1 = 'domain:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69|67  \n'
         
        self.assertEqual(s1, s, 'parse from test-data test')
         
        mInfo.CheckMinerHashRate('domain')
        mInfo.CheckMinerTemp('domain')
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
         
        log.info("running test: low hashrate test")
         
        mInfo = MinerInfo()
         
        mInfo.SetMinerRawHtmlData('domain', open('test-data/lowHashRate.html', 'r').read())
        mInfo.ParseMinerInfo('domain')
         
        msg = ''
         
        try:
            mInfo.CheckMinerHashRate('domain')
        except ValueError as v:
            msg = v.message
         
        self.assertTrue(msg, 'low hashrate test')
         
        mInfo.CheckMinerTemp('domain')
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
         
        log.info("running test: high temp test")
 
        mInfo = MinerInfo()
         
        mInfo.SetMinerRawHtmlData('domain', open('test-data/highTemp.html', 'r').read())
        mInfo.ParseMinerInfo('domain')
         
        msg = ''
         
        try:
            mInfo.CheckMinerTemp('domain')
        except ValueError as v:
            msg = v.message
         
        self.assertTrue(msg, 'too high temp test')
         
        mInfo.CheckMinerHashRate('domain')
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
         

        log.info("running test: Parse error 1")
         
        mInfo = MinerInfo()
         
        mInfo.SetMinerRawHtmlData('domain', open('test-data/parseError.html', 'r').read())
         
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
        mInfo.ParseMinerInfo('domain')
        self.assertTrue(mInfo.GetMessageToSend(), "should be message")
  
        
        log.info("running test: Parse error 2")
         
        mInfo = MinerInfo()
         
        mInfo.SetMinerRawHtmlData('domain', open('test-data/parseError2.html', 'r').read())
         
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
        mInfo.ParseMinerInfo('domain')
        self.assertTrue(mInfo.GetMessageToSend(), "should be message")
         
         
        log.info("running test: Parse error 3")
         
        mInfo = MinerInfo()
         
        mInfo.SetMinerRawHtmlData('domain', open('test-data/parseError3.html', 'r').read())
         
        self.assertFalse(mInfo.GetMessageToSend(), "should be no message")
        mInfo.ParseMinerInfo('domain')
        self.assertTrue(mInfo.GetMessageToSend(), "should be message")
         
        
        log.info("running test: Mock test for network") 
         
        with Mock() as urllib2Mock:
 
            theurl = 'http://%s/cgi-bin/minerStatus.cgi' % 'domain'
 
            passman = urllib2Mock.HTTPPasswordMgrWithDefaultRealm()
             
            passman.add_password(None, theurl, _USERNAME, _PASSWORD)
             
            authhandler = urllib2Mock.HTTPDigestAuthHandler(passman)
             
            opener = urllib2Mock.build_opener(authhandler)
            urllib2Mock.install_opener(opener)
             
            pagehandle = urllib2Mock.urlopen(theurl)
     
            rawData =   open('test-data/testOk.html', 'r').read()
     
            pagehandle.read() >> rawData
         
        mInfo = MinerInfo(['domain'])
        mInfo.SetLibraries(None, urllib2Class=urllib2Mock)
         
        s = mInfo.Info()
         
        self.assertEqual("domain:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69|67  \n", 
                         s, "urllib2 mock test")
         
        urllib2Mock.validate()
        
        
        log.info("running test: Mock test for notifier") 
         
        with Mock() as urllib2Mock:
 
            theurl = 'http://%s/cgi-bin/minerStatus.cgi' % 'domain'
 
            passman = urllib2Mock.HTTPPasswordMgrWithDefaultRealm()
             
            passman.add_password(None, theurl, _USERNAME, _PASSWORD)
             
            authhandler = urllib2Mock.HTTPDigestAuthHandler(passman)
             
            opener = urllib2Mock.build_opener(authhandler)
            urllib2Mock.install_opener(opener)
         
             
            pagehandle = urllib2Mock.urlopen(theurl)
     
            rawData =   open('test-data/lowHashRate.html', 'r').read()
     
            pagehandle.read() >> rawData
 
        with Mock() as notifierMock:
             
            notifierMock().NotifyRaw('Some error with miners', 'miner domain hashrate is to low (11845 < 14004 - 10 percent)\n\ndomain:  11,845.93 (13,849.65) [14,004.90]  0.0007%  13d8h26m24s     OK  75 96 78      69|65  \n')
 
        mInfo = MinerInfo(['domain'], notifySingle=True)
        mInfo.SetLibraries(notifierClass=notifierMock, urllib2Class=urllib2Mock)
         
        s = mInfo.Info()
         
        self.assertEqual("domain:  11,845.93 (13,849.65) [14,004.90]  0.0007%  13d8h26m24s     OK  75 96 78      69|65  \n", 
                         s, "notifier mock test")
         
        notifierMock.validate()
        urllib2Mock.validate()


        log.info("running test: Mutithreaded test")
                
        with Mock() as urllib2Mock1:

            theurl = 'http://%s/cgi-bin/minerStatus.cgi' % 'domain'

            passman = urllib2Mock1.HTTPPasswordMgrWithDefaultRealm()
            
            passman.add_password(None, theurl, _USERNAME, _PASSWORD)
            
            authhandler = urllib2Mock1.HTTPDigestAuthHandler(passman)
            
            opener = urllib2Mock1.build_opener(authhandler)
            urllib2Mock1.install_opener(opener)
        
            
            pagehandle = urllib2Mock1.urlopen(theurl)
    
            rawData =   open('test-data/testOk.html', 'r').read()
    
            pagehandle.read() >> rawData
        
        with Mock() as urllib2Mock2:
 
            theurl = 'http://%s/cgi-bin/minerStatus.cgi' % 'domain2'
 
            passman = urllib2Mock2.HTTPPasswordMgrWithDefaultRealm()
             
            passman.add_password(None, theurl, _USERNAME, _PASSWORD)
             
            authhandler = urllib2Mock2.HTTPDigestAuthHandler(passman)
             
            opener = urllib2Mock2.build_opener(authhandler)
            urllib2Mock2.install_opener(opener)
         
             
            pagehandle = urllib2Mock2.urlopen(theurl)
     
            rawData =   open('test-data/testOk.html', 'r').read()
     
            pagehandle.read() >> rawData
            
        with Mock() as notifierMock1:
            pass
        
        with Mock() as notifierMock2:
            pass
        
        domains = ['domain', 'domain2']
        urllib2s = [urllib2Mock1, urllib2Mock2]
        notifiers = [notifierMock1, notifierMock2]
         
        multi = MinerInfoMultithreaded(domains, notifiers, urllib2s)
         
        d, s = multi.MakeAllInfo()
        
        textResult = """domain:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69|67  
domain2:  13,829.06 (13,849.75) [14,004.90]  0.0007%  13d7h38m34s     OK  75 95 78      69|67  
"""

        messageResult = ''
        
        self.assertEqual(d, textResult, "comparing text")
        self.assertEqual(s, messageResult, "comparing message to send text")
        
        urllib2Mock1.validate()
        urllib2Mock2.validate()
        notifierMock1.validate()
        notifierMock2.validate()
        
        
        


if __name__ == "__main__":
    
    parser = OptionParser(usage = "usage: %prog [options]", version = "%prog " + _VERSION_)    
    
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="Show debug messages")
    
    parser.add_option("-n", "--no-mail-notify",
                      action="store_true", dest="noNotify", default=False,
                      help="Do not send any email notifications")

    parser.add_option("-f", "--auto-refresh",
                      action="store_true", dest="autoRefresh", default=False,
                      help="Auto refresh data on console")

    parser.add_option("-t", "--auto-refresh-time", type="int",
                      action="store", dest="autoRefreshTime", default=3,
                      help="Auto refresh time. Valid for -f option only. Default value 3 seconds")

    
    (options, args) = parser.parse_args()
        
    if options.verbose:
        console.setLevel(logging.DEBUG)    
    
    if args:
        parser.print_help()
        exit(-1)

    if options.autoRefresh:

        console.setLevel(logging.CRITICAL)

        os.system('cls' if os.name == 'nt' else 'clear')
    
        print 'requestig...'
      
        while True:            
            
            multiInfo = MinerInfoMultithreaded(_MINERS)
         
            myData, mySend = multiInfo.MakeAllInfo()
            
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print '[*] Info ' + datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
            print myData
            print '[*] Errors'
            print mySend
            
            time.sleep(options.autoRefreshTime)
            
    multiInfo = MinerInfoMultithreaded(_MINERS)
         
    myData, mySend = multiInfo.MakeAllInfo()
    
    log.info("%s", myData)
    
    if mySend:
        if not options.noNotify:
            Notifier().NotifyRaw("Miner errors", mySend)
        else:
            print '[!] Errors:'
            print mySend
    
            
 
        
