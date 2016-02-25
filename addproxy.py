#!/usr/bin/env python
import requests, json

happyTokenFilename = "happy_proxy"

def run():
	#get happy proxy token
	token = ""
	with open(happyTokenFilename) as f:
		token = f.readline().rstrip()

	#make request for proxies
	r = requests.get("https://happy-proxy.com/fresh_proxies?key=" + token)

	#parse received json if successful request
	if r.status_code == 200 and r.text != "":
		result = json.loads(r.text)
	else:
		return

	#print type(result)
	#print result
	proxies = []
	#parse data to get a list of lists
	#each item in the bigger list will be a list containing the IP and port
	#of the proxy
	for entry in result:
		temp = entry["ip_port"]
		vals = temp.split(":")
		proxies.append(vals)
	
	for p in proxies:
		print p[0] + ":" + p[1]

def main():
	run()

if __name__ == "__main__":
	main()

