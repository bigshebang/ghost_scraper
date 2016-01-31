#!/usr/bin/env python
import requests
import time
from multiprocessing import Process, Lock
import platform
import subprocess as sub

urls = []
permFilename = "permutations"
#currentFilename = ".current"
proxyFilename = "proxies"
logFilename = ".ghost_scraper.log"
safeTries = 7 #safe number of URLs to try at once. not changeable
current = 0

#make 7 requests via the given proxy for the given URLs
#also manage URLs and if this proxy turns bad
#return true if the proxy is still working by the end
#return false and stop if the proxy gets 420s (blocked)
def scrape(urls, p):
	urls = []
#	while true: #do this forever! or until no URLs left to try
#		#use lock and get next set of URLs to try
#		permLock.acquire()
#		getURLs(urls)
#		permLock.release()

#		#use lock and get next proxy from file
#		proxyLock.acquire()
#		proxy = getProxy()
#		proxyLock.release()
	proxy = {
		"https" : p
	}

	#try the seven URLs
	for i in range(0, safeTries):
		ret = tryURL(urls[i], proxy)

		#if we get blocked return false
		if ret == 420:
			#removeProxy() #get rid of proxy from proxylist
			return false
		else: #successfully tried to get the URL
			urls[i]["status"] = 1
	
	return true

#makes get request to given URL with given proxies
#return status code
def tryURL(url, p):
	r = requests.get("https://ghostbin.com/paste/" + url + "/raw",
		proxies=p)
	print r.status_code,
	if r.status_code != 404:
		print r.text
	else:
		print ""
	if r.status_code == 200 and r.text != "":
		with open("results/" + url, "w") as f:
			f.write(r.text)

	return r.status_code

#return list of dictionaries, each containing a URL and its status
def getURLs(f, urls=[]):
	if not urls: #if blank array
		#get urls and set status to 0
		for i in range(0, safeTries):
			line = f.readline()
			urls[i] = {
				"url" : line,
				"status" : 0
			}
	else: #not new, already has URLs in it
		for i in range(0, safeTries):
			#if we see a URL that didn't get tested, the rest are untested
			#so we don't need to add any new ones
			if urls[i]["status"] == 0:
				break

			line = f.readline()
			urls[i] = {
				"url" : line,
				"status" : 0
			}
	
	return urls

#return a proxy as a string from the file
def getProxy(f):
	#code

#count num lines in a given file
def getLines(filename):
	#if nix, just use wc cuz it's way faster
	os = platform.system().lower()
	if os != "windows" and os != "unknown":
		cmdList = ["wc", "-l", filename]
		p = sub.Popen(cmdList,stdout=sub.PIPE,stderr=sub.PIPE)
		output, errors = p.communicate()
		return output.split(" ")[0]
	else: #count lines via reading file in with python
		with open(filename, "r") as f:
			return sum(1 for _ in f)

def main():
	proxyBuffer = 15 #15 seconds to sleep in between using the same proxy
	numProc = 4 #default. TODO: let user choose this. use arg parse
	numProxies = getLines(proxyFilename)
	done = False

	#if we're going to use a cycle in two consecutive attempts we need to
	#sleep in between
	if numProc * 2 + 1 >= numProxies:
		sleep = True
	else:
		sleep = False

	#variables needed
	p = [] #holds processes
	urls = [] #holds list of list of dictionaries containing URLs
	proxies = [] #list of proxies stored as strings

	#open files for URLs and proxies
	permFile = open(permFilename, "r")
	proxyFile = open(proxyFilename, "r")

	#get initial set of URLs and proxies
	for i in range(0, numProc):
		urls[i] = getURLs(permFile)
		proxies[i] = getProxy(proxyFile)

	#start initial processes
	for num in range(0, numProc):
		p[num] = Process(target=scrape, args=(urls[num], proxies[num]))
		p[num].start()

	#while processes run, keep checking them so we can reconfigure and restart
	#them when they die
	while not done:
		for num in range(0, numProc):
			if not p[num].is_alive(): #check if process is finished
				if sleep: #sleep if too many more processes than proxies
					time.sleep(proxyBuffer)

				#get new URLs and proxy
				urls[num] = getURLs(permFile)
				proxies[num] = getProxy(proxyFile)

				#if no more URLs or proxies left, we are done
				if urls[num] == None or proxies[num] == None:
					done = True
					break

				#start process with new data
				p[num] = Process(target=scrape, args=(urls[num], proxies[num]))
				p[num].start()

		time.sleep(1)

if __name__ == "__main__":
	main()

