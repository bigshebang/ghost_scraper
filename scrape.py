#!/usr/bin/env python
import requests
import time
from multiprocessing import Process, Lock
import platform
import subprocess as sub
import shutil

urls = []
permFilename = "permutations"
proxyFilename = "proxies"
badProxyfilename = ".bad_proxies"
logFilename = ".ghost_scraper.log"
safeTries = 7 #safe number of URLs to try at once. not changeable
current = 0

#make 7 requests via the given proxy for the given URLs
#also manage URLs and if this proxy turns bad
#return true if the proxy is still working by the end
#return false and stop if the proxy gets 420s (blocked)
def scrape(urls, p):
	proxy = {
		"https" : p
	}

	#try the seven URLs
	for i in range(0, safeTries):
		#if we already looked at this, skip to next
		if urls[i]["status"] == 1:
			continue

		ret = tryURL(urls[i], proxy)

		#if we get blocked return false
		if ret == 420:
			removeProxy() #get rid of proxy from proxylist
			return false
		else: #successfully tried to get the URL
			urls[i]["status"] = 1
	
	return true

#makes get request to given URL with given proxies
#return status code
def tryURL(url, p):
	#TODO: add a try/catch all around the GET request
	try:
		r = requests.get("https://ghostbin.com/paste/" + url + "/raw",
			proxies=p)
	except: #error so proxy is probably bad
		return 420

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
#status 0 means it hasn't been attempted successfully yet and 1 means it has
def getURLs(f, urls=[]):
		#get urls and set status to 0
		for i in range(0, safeTries):
			#if status is 0 then the rest are also 0 so we're done
			if i < len(urls) and urls[i]["status"] == 0:
				break

			#get URL and put in list. if end of file we're done
			line = f.readline().rstrip()
			if line == "":
				if i == 0: #this means first thing we read is empty file
					#check if there are any URLs leftover from last time
					for j in range(0, safeTries):
						if urls[j]["status"] == 0: #still some URLs left
							return urls

					urls = None
					return None #we are done
				else
					break

			urls[i] = {
				"url" : line,
				"status" : 0
			}
	
	return urls

#return a proxy as a string from the file
def getProxy(f, proxies=[], index=0):
	#get a new proxy
	line = f.readline().rstrip()

	#if end of file, start from beginning of file and try again
	if line == "":
		f.flush()
		line = f.readline().rstrip()

		if line == "": #if file is empty, no more proxies left
			#code

	counter = 0	
	while line in proxies and not proxyCheck(line): #if proxy in use already
		line = f.readline().rstrip()

		#this means we ran very low on proxies. sleep before trying again
		if line == "":
			if counter > 100: #tried 100 times, probably time to stop
				proxies[index] = None
				return None

			sleep 5

		counter += 1

	proxies[index] = line

#will remove a given proxy from the proxy list file
def removeProxy(f, proxy):
	#add bad proxy to bad proxies list
	with open(badProxyFilename, "a") as badProxyFile:
		badProxyFile.write(proxy + "\n")

	#get current position in file
	current = f.tell() - len(proxy) + 1
	f.flush() #go to beginning of file to read in all proxies
	lines = []
	line = f.readline().rstrip()

	#read in lines until we hit the end of the file
	while line != "":
		if line != proxy: #if it isn't the bad proxy, remember it
			lines.append(line)

		line = f.readline().rstrip()
	
	#move file to backup
	f.close()
	shutil.move(proxyFilename, ".old_" + proxyFilename)

	#write new file without bad proxy
	with open(proxyFilename, "w") as outfile:
		for p in lines:
			outfile.write(p + "\n")
	
	#we can get rid of backup proxy list cuz we made the other one now
	shutil.rmtree(".old_" + proxyFilename)

	#go back to where we were in the file
	f = open(proxyFilename, "r")
	f.seek(current, 0)

#check if proxy works and can connect to the internet with it
#return true if it's good, false if it's not
def proxyCheck(proxy):
	proxies = {
		"https" : proxy
	}

	try:
		r = requests.get("https://www.google.com", proxies=proxies)
	except:
		return false
	
	return true

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

	#we want there to be many more proxies than processes using proxies
	#because if we use a proxy consecutively it will get blocked and it's
	#better to keep as many proxies alive as possible. if not enough proxies
	#then we will sleep for proxyBuffer seconds in between scrapes
	if numProc * 4 + 1 >= numProxies:
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
		proxies[i] = getProxy(proxyFile, index=i)

	#start initial processes
	for num in range(0, numProc):
		p[num] = Process(target=scrape, args=(urls[num], proxies[num]))
		p[num].start()

	#while processes run, keep checking them so we can reconfigure and restart
	#them when they die
	while not done:
		for num in range(0, numProc):
			if not p[num].is_alive(): #check if process is finished
				if sleep: #sleep if too many processes compared to proxies
					time.sleep(proxyBuffer)

				#get new URLs and proxy
				getURLs(permFile, urls=urls[num])
				getProxy(proxyFile, proxies=proxies, index=num)

				#if no more URLs or proxies left, we are done
				if urls[num] == None or proxies[num] == None:
					done = True
					break

				#start process with new data
				p[num] = Process(target=scrape, args=(urls[num], proxies[num]))
				p[num].start()

		time.sleep(1)
	
	print "It seems that either all proxies were exhausted or all URLs were"
		  + "tested successfully."

if __name__ == "__main__":
	main()

