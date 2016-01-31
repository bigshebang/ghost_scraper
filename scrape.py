#!/usr/bin/env python
import requests
import time
from multiprocessing import Process

urls = []

def tryURL(index, p):
	#r = requests.get("https://ghostbin.com/paste/" + urls[index]["url"] + "/raw",
	start = time.clock()
	r = requests.get("https://ghostbin.com/paste/" + index + "/raw",
		proxies=p)
	end = time.clock()
	print r.status_code,
	if r.status_code != 404:
		print r.text
	else:
		print ""
	#if r.status_code == 200 and r.text != "":
		#write to file results/url

	#if r.status_code == 404 or r.status_code == 420:
	#	urls[index][""]

def main():
	proxies = {
		#"https" : "221.178.181.198:80"
		"https" : "192.99.71.135:3128"
	}

	for i in range(1, 8):
		print i,
	#	start = time.time()
		tryURL("r3bz" + str(i), proxies)
	#	end = time.time()
	#	diff = end - start
	#	if diff < 5:
#			time.sleep(int(5 - diff))
		#time.sleep(3)

	time.sleep(15)	
	for i in range(1, 8):
		print i,
		tryURL("hj1k" + str(i), proxies)

	#print (i + 1),
	#tryURL("hzqxc", proxies)
	#	r = requests.get("https://ghostbin.com/paste/ab5x" + str(i) + "/raw", proxies=proxies)
	#	print i, r.status_code, r.text
	

if __name__ == "__main__":
	main()

