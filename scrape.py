#!/usr/bin/env python
import requests, time, platform, shutil, argparse, sys, os
from multiprocessing import Process, Lock
import subprocess as sub

currentFilename = ".current"
permFilename = "permutations"
proxyFilename = "proxies"
badProxyfilename = ".bad_proxies"
safeTries = 7 #safe number of URLs to try at once. not changeable
current = 0
args = ""
numProxies = 0

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
			if args.v > 2:
				print "[-] url %s already looked at, skipping" % (url)

			continue

		ret = tryURL(urls[i], proxy)

		#if we get blocked return false
		if ret == 420:
			if args.v > 0:
				print "[-] " + p + " has been blocked for 24 hours"

			removeProxy() #get rid of proxy from proxylist
			return false
		else: #successfully tried to get the URL
			urls[i]["status"] = 1
	
	return true

#makes get request to given URL with given proxies
#return status code
def tryURL(url, p):
	try:
		if args.v > 2:
			print "[+] making request to '%s'" % (p)

		r = requests.get("https://google.com")
		#r = requests.get("https://ghostbin.com/paste/" + url + "/raw",
		#	proxies=p)
	except: #error so proxy is probably bad
		return 420

	if r.status_code == 200 and r.text != "":
		if args.v == 1:
			print "[+] found valid paste at " + url
		elif args.v > 1:
			print "[+] got status code %d for %s" % (r.status_code, url)

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

				if args.v > 0:
					print "[-] No more URLs to scrape"

				urls = None
				return None #we are done
			else:
				break

		urls[i] = {
			"url" : line,
			"status" : 0
		}

	with open(currentFilename, "w") as currentFile:
		currentFile.write(f.tell())

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
			proxies[index] = None
			return None
	
	counter = 0	
	while line in proxies and not proxyCheck(f, line): #if proxy in use already
		line = f.readline().rstrip()

		#this means we ran very low on proxies. sleep before trying again
		if line == "":
			if counter > 30: #tried 100 times, probably time to stop
				if args.v > 0:
					print "[-] All proxies exhausted"

				proxies[index] = None
				return None

			if args.v > 1:
				print "[-] couldn't find free working proxy in list, sleeping 5"
			time.sleep(5)

		counter += 1

	proxies[index] = line

#will remove a given proxy from the proxy list file
def removeProxy(f, proxy):
	#decrement number of proxies
	numProxies -= 1

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
def proxyCheck(f, proxy):
	proxies = {
		"https" : proxy
	}

	try:
		r = requests.get("https://www.google.com", proxies=proxies)
	except:
		removeProxy(f, proxy)
		if args.v > 0:
			print "[-] proxy %s has a connection issue" % proxy
		return false
	
	return true

#count num lines in a given file
def getLines(filename):
	#if nix, just use wc cuz it's way faster
	OS = platform.system().lower()
	if OS != "windows" and OS != "unknown":
		cmdList = ["wc", "-l", filename]
		p = sub.Popen(cmdList,stdout=sub.PIPE,stderr=sub.PIPE)
		output, errors = p.communicate()
		return output.split(" ")[0]
	else: #count lines via reading file in with python
		with open(filename, "r") as f:
			return sum(1 for _ in f)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-p", "--processes",
						help="Number of processes to use when scraping",
						type=int)
	parser.add_argument("-v", help="Increase output verbosity", action="count")

	global numProxies
	global args
	args = parser.parse_args()
	if args.processes != None and args.processes < 1:
		print "Processes must be a positive number"
		return -1

	proxyBuffer = 15 #15 seconds to sleep in between using the same proxy
	numProc = 4 #default. TODO: let user choose this. use arg parse
	numProxies = getLines(proxyFilename)
	done = False
	sleep = False

	#we want there to be many more proxies than processes using proxies
	#because if we use a proxy consecutively it will get blocked and it's
	#better to keep as many proxies alive as possible. if not enough proxies
	#then we will sleep for proxyBuffer seconds in between scrapes
	if numProc * 4 + 1 >= numProxies:
		if args.v > 1:
			print "[-] Too many processes compared to proxies"

		sleep = True

	#variables needed
	p = [] #holds processes
	urls = [] #holds list of list of dictionaries containing URLs
	proxies = [] #list of proxies stored as strings

	#open files for URLs and proxies
	permFile = open(permFilename, "r")
	proxyFile = open(proxyFilename, "r")

	#check if we have already tried some URLs and go to correct spot in file
	if os.path.isfile(currentFilename):
		if args.v > 0:
			print "[+] found previous scraping spot"
		with open(currentFilename) as tempFile: #get file position
			dest = tempFile.readline().rstrip()
			permFile.seek(dest, 0) #move to file position

			if args.v > 1:
				print "[+] Moving up %d bytes in the file" % dest

	#get initial set of URLs and proxies
	for i in range(0, numProc):
		urls[i] = getURLs(permFile)
		proxies[i] = getProxy(proxyFile, index=i)

	#start initial processes
	for num in range(0, numProc):
		if args.v > 2:
			print "[+] starting process " + str(num)

		p[num] = Process(target=scrape, args=(urls[num], proxies[num]))
		p[num].start()

	#while processes run, keep checking them so we can reconfigure and restart
	#them when they die
	while not done:
		for num in range(0, numProc):
			if not p[num].is_alive(): #check if process is finished
				if args.v > 0:
					print ("[+] process %d is done, restarting with new data"
						   % num)

				if sleep: #sleep if too many processes compared to proxies
					if args.v > 1:
						print "[+] sleeping for %d seconds" % (proxyBuffer)

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

		if numProc * 4 + 1 >= numProxies:
			if args.v > 1:
				print ("[-] Too many proxies have been lost, now need sleep"
					  + " between process resets")
			sleep = True

		time.sleep(1)

	print ("[+] It seems that either all proxies were exhausted or all URLs were"
		   + " tested successfully")

	return 0

if __name__ == "__main__":
	sys.exit(main())

