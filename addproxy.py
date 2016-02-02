#!/usr/bin/env python
import requests

happyTokenFilename = "happy_proxy"

def run():
	#get happy proxy token
	token = ""
	with open(happyTokenFilename) as f:
		token = f.readline().rstrip()
	
	#code
	print token

#def main():
#	run()

#if __name__ == "__main__":
#	main()

