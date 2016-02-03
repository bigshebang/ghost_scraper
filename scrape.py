#!/usr/bin/env python
import requests, time, platform, shutil, argparse, sys, os
from multiprocessing import Process, Queue
import subprocess as sub

currentFilename = ".current"
permFilename = "permutations"
permFile = ""
proxyFilename = "proxies"
proxyFile = ""
badProxyFilename = ".bad_proxies"
blockedProxyFilename = ".blocked_proxies"
safeTries = 7 #safe number of URLs to try at once. not changeable
args = ""
numProxies = 0

#make 7 requests via the given proxy for the given URLs
#also manage URLs and if this proxy turns bad
#return true if the proxy is still working by the end
#return false and stop if the proxy gets 420s (blocked)
def scrape(urls, p, q):
	if args.v > 2:
		print "process started"

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

		ret = tryURL(urls[i]["url"], proxy)

		#if we get blocked return false
		if ret == 420 or ret == 5000:
			if args.v > 0:
				if ret == 420:
					print "[-] " + p + " has been blocked for 24 hours"
				else:
					print "[-] there was an error with %s, assuming blocked" % p

			removeProxy(p, blocked=True) #get rid of proxy from proxylist
			break
		else: #successfully tried to get the URL
			urls[i]["status"] = 1

	q.put(urls)

#makes get request to given URL with given proxies
#return status code
def tryURL(url, p):
	try:
		if args.v > 2:
			print "[+] making request to '%s' via '%s'" % (url, p)

		r = requests.get("https://ghostbin.com/paste/" + url + "/raw",
			proxies=p, timeout=30)
	except: #error so proxy is probably bad
		return 5000

	if r.status_code == 200 and r.text != "":
		if args.v == 1:
			print "[+] found valid paste at " + url
		elif args.v > 1:
			print "[+] got status code %d for %s" % (r.status_code, url)

		with open("results/" + url, "w") as f:
			f.write(r.text.encode("utf8"))

	return r.status_code

#return list of dictionaries, each containing a URL and its status
#status 0 means it hasn't been attempted successfully yet and 1 means it has
def getURLs(u):
	global permFile #so we can modify global var

	if not u:
		for i in range(0, safeTries):
			u.append("")

	#get urls and set status to 0
	for i in range(0, safeTries):
		#if status is 0 then the rest are also 0 so we're done
		if "status" in u[i] and u[i]["status"] == 0:
			if args.v > 1:
				print ("url %s has status of 0, so all following URLs do also"
					   % u[i])

			break

		#get URL and put in list. if end of file we're done
		line = permFile.readline().rstrip()
		if line == "":
			if i == 0: #this means first thing we read is empty file
				#check if there are any URLs leftover from last time
				for j in range(0, safeTries):
					if u[j]["status"] == 0: #still some URLs left
						return u

				if args.v > 0:
					print "[-] No more URLs to scrape"

				#out of URLs
				u = None

			break

		u[i] = {
			"url" : line,
			"status" : 0
		}

	with open(currentFilename, "w") as currentFile:
		read = str(permFile.tell())
		currentFile.write(read)

		if args.v > 2:
			print "Read %s bytes, writing to .current" % read

	return u

#return a proxy as a string from the file
def getProxy(proxies, index):
	global proxyFile #so we can modify global var

	#get a new proxy
	line = proxyFile.readline().rstrip()

	#if end of file, start from beginning of file and try again
	if line == "":
		proxyFile.seek(0, 0)
		line = proxyFile.readline().rstrip()

		if line == "": #if file is empty, no more proxies left
			if args.v > 0:
				print "[-] No more proxies left"

			proxies[index] = None
			return proxies[index]
	
	counter = 0	
	while line in proxies and not proxyCheck(line): #if proxy in use already
		line = proxyFile.readline().rstrip()

		#this means we ran very low on proxies. sleep before trying again
		if line == "":
			if counter > 30: #tried 100 times, probably time to stop
				if args.v > 0:
					print "[-] All proxies exhausted"

				proxies[index] = None
				break

			if args.v > 1:
				print "[-] couldn't find free working proxy in list, sleeping 5"

			time.sleep(5) #sleep to wait for new proxy


		time.sleep(1) #small sleep cuz there should be more proxies
		counter += 1

	proxies[index] = line
	return proxies[index]

#will remove a given proxy from the proxy list file
def removeProxy(proxy, blocked=False):
	#so we can edit global vars
	global proxyFile
	global numProxies

	#decrement number of proxies
	numProxies -= 1

	#if proxy was blocked put in blocked proxy list, we can reuse in 24 hrs
	if blocked:
		with open(blockedProxyFilename, "a") as blockedProxyFile:
			blockedProxyFile.write(proxy + "\n")
	else: #proxy didn't work, so probably just a bad proxy
		with open(badProxyFilename, "a") as badProxyFile:
			badProxyFile.write(proxy + "\n")

	#get current position in file
	current = proxyFile.tell() - len(proxy) + 1
	proxyFile.seek(0, 0) #go to beginning of file to read in all proxies
	lines = []
	line = proxyFile.readline().rstrip()

	#read in lines until we hit the end of the file
	while line != "":
		if line != proxy: #if it isn't the bad proxy, remember it
			lines.append(line)

		line = proxyFile.readline().rstrip()
	
	#move file to backup
	proxyFile.close()
	shutil.move(proxyFilename, ".old_" + proxyFilename)

	#write new file without bad proxy
	with open(proxyFilename, "w") as outfile:
		for p in lines:
			outfile.write(p + "\n")
	
	#we can get rid of backup proxy list cuz we made the other one now
	if os.path.isfile(".old_" + proxyFilename): #only if file exists
		os.remove(".old_" + proxyFilename)

	#go back to where we were in the file
	proxyFile = open(proxyFilename, "r")
	proxyFile.seek(current, 0)

#check if proxy works and can connect to the internet with it
#return true if it's good, false if it's not
def proxyCheck(proxy):
	proxies = {
		"https" : proxy
	}

	try:
		r = requests.get("https://www.google.com", proxies=proxies, timeout=45)
		if args.v > 2:
			print "[+] proxy %s seems like a valid proxy" % proxy
	except:
		removeProxy(proxy)
		if args.v > 0:
			print "[-] proxy %s has a connection issue" % proxy
		return False
	
	return True

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

	#so we can edit global vars
	global numProxies
	global args
	global permFile
	global proxyFile

	#default number of processes
	numProc = 4

	args = parser.parse_args()
	if args.processes != None and args.processes < 1:
		print "Processes must be a positive number"
		return -1
	elif args.processes != None:
		numProc = args.processes

	#setup some vars
	proxyBuffer = 15 #15 seconds to sleep in between using the same proxy
	numProxies = getLines(proxyFilename)
	done = False
	sleep = False

	#we want there to be many more proxies than processes using proxies
	#because if we use a proxy consecutively it will get blocked and it's
	#better to keep as many proxies alive as possible. if not enough proxies
	#then we will sleep for proxyBuffer seconds in between scrapes
	if numProxies != "" and numProxies != "0": #make sure numProxies isn't blank
		numProxies = int(numProxies)
		if (numProc * 4 + 1) >= numProxies:
			if args.v > 1:
				print "[-] Too many processes compared to proxies"

			sleep = True
	else:
		print "No proxies given"
		return 1

	#variables needed
	q = [] #holds Queue objects
	p = [] #holds processes
	urls = [] #holds list of list of dictionaries containing URLs
	proxies = [] #list of proxies stored as strings

	#initialize all lists
	for i in range(0, numProc):
		q.append(Queue())
		p.append("")
		urls.append([])
		proxies.append("")

	#open files for URLs and proxies
	permFile = open(permFilename, "rb")
	proxyFile = open(proxyFilename, "rb")

	#check if we have already tried some URLs and go to correct spot in file
	if os.path.isfile(currentFilename):
		if args.v > 0:
			print "[+] found previous scraping spot"
		with open(currentFilename) as tempFile: #get file position
			dest = tempFile.readline().rstrip()

			#if str isn't empty, move to that position in the file
			if dest != "":
				dest = int(dest)
				permFile.seek(dest, 0) #move to file position

				if args.v > 1:
					print "[+] Moving up %d bytes in the file" % dest
			else:
				if args.v > 0:
					print "[-] no value found in history file"

	#get initial set of URLs and proxies
	for i in range(0, numProc):
		urls[i] = (getURLs([]))
		proxies[i] = getProxy(proxies, i)

	#start initial processes
	for num in range(0, numProc):
		if args.v > 2:
			print "[+] starting process " + str(num)

		p[num] = Process(target=scrape, args=(urls[num], proxies[num], q[i]))
		p[num].start()
	
	#while processes run, keep checking them so we can reconfigure and restart
	#them when they die
	while not done:
		for num in range(0, numProc):
			if not p[num].is_alive(): #check if process is finished
				if args.v > 0:
					print ("[+] process %d is done, restarting with new data"
						   % num)
				
				#get urls updated var from process if not empty
				if not q[num].empty():
					urls[num] = q[num].get()

				#get new URLs and proxy
				urls[num] = getURLs(urls[num])
				proxies[num] = getProxy(proxies, num)

				#if no more URLs or proxies left, we are done
				if urls[num] == None or proxies[num] == None:
					done = True
					break

				#sleep if too many processes compared to proxies
				if sleep:
					if args.v > 1:
						print "[+] sleeping for %d seconds" % (proxyBuffer)

					time.sleep(proxyBuffer)

				#start process with new data
				p[num] = Process(target=scrape, args=(urls[num], proxies[num],
								 q[num]))
				p[num].start()

		if not sleep and numProc * 4 + 1 >= numProxies:
			if args.v > 1:
				print ("[-] Too many proxies have been lost, now need sleep"
					  + " between process resets")
			sleep = True

		if args.v > 2:
			print "all processes checked on, sleeping for 1 second"

		time.sleep(1)

	print ("[+] It seems that either all proxies were exhausted or all URLs were"
		   + " tested successfully")
	print "[+] waiting for all processes to finish"

	for i in range(0, numProc):
		p[i].join()

	return 0

if __name__ == "__main__":
	ret = main() #call main

	if args.v > 2:
		print "in main if statement, program quitting"

	sys.exit(ret)

