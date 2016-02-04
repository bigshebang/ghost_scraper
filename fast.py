#!/usr/bin/env python
import requests, sys, time, os

def main():
	count = 0
	permFilename = "permutations"
	currentFilename = ".fast_current"
	permFile = open(permFilename)

	#check if we have already tried some URLs and go to correct spot in file
	if os.path.isfile(currentFilename):
		print "[+] found previous scraping spot"
		with open(currentFilename) as tempFile: #get file position
			dest = tempFile.readline().rstrip()

			#if str isn't empty, move to that position in the file
			if dest != "":
				dest = int(dest)
				permFile.seek(dest, 0) #move to file position

				print "[+] Moving up %d bytes in the file" % dest
			else:
				print "[-] no value found in history file"

	line = permFile.readline().rstrip()

	#until no more URLs to try
	while line != "":
		sys.stdout.flush()
		currentPos = permFile.tell()
		with open(currentFilename, "w") as currentFile:
			currentFile.write(str(currentPos))

		try:
			print "requesting %s" % line + " ...",
			r = requests.get("https://ghostbin.com/paste/" + line + "/raw",
							 timeout=30)
			count += 1
		except: #error so proxy is probably bad
			print "connection error, maybe blocked"

		if r.status_code == 200 and r.text != "":
			print "found valid paste at " + line + "!"
			print "[+] got status code %d for %s" % (r.status_code, line)

			with open("results/" + url, "w") as f:
				f.write(r.text.encode("utf8"))
		elif r.status_code == 420: #blocked so go up a line in the current file
			print "received 420, blocked :("
			with open(currentFilename, "w") as currentFile:
				currentFile.write(str(currentPos - 6))

			return 0
		else:
			print "Nothing found"

		line = permFile.readline().rstrip()

		#number of safe continuous requests
		if count >= 7:
			count = 0
			print "Sleeping 20..."
			sys.stdout.flush()
			time.sleep(20)

	return 0

if __name__ == "__main__":
	sys.exit(main())	

