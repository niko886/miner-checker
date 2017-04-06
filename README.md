# miner-checker

Simple program that helps you to watch what happening with your miners in *realtime*

## Features 

* Show you realtime information
* Notifies you on email, if any errors

## Install and run

* Setup python 2.x or 3.x
* Make conf.py from conf.py.example with your own data
* Run mine.py from console

## Output explained

		<1>            <2>       <3>         <4>          <5>        <6>          <7> <8>           <9>
		192.168.0.90:  13,552.15 (13,414.26) [14,004.90]  0.0007%     1d40m4s     OK  71 95 73      91|69
		192.168.0.91:  11,796.09 (11,670.20) [11,850.30]  0.0029%    1d39m17s     OK  83 95 80      61|48
		192.168.0.92:  11,753.55 (11,588.66) [11,850.30]  0.0029%     1d39m8s     OK  77 97 88      61|53
		...
		

1. IP address
2. Current hashrate
3. Average hashrate
4. Ideal hashrate
5. HW %
6. Uptime
7. Asic status, OK if no errors
8. Chip temp
9. Fan speed in percent. 100% = 5880rpm


