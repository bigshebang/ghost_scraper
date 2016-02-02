# ghost_scraper
Scraper for ghostbin.com.

This script requires a text file of HTTPS proxies that you must provide in a file called 'proxies'. Put each proxy on a line by itself in the format of x.x.x.x:xx. You can prepend it with 'http://' or 'https://' if desired but it isn't necessary. The script assumes that you don't have any repeat proxies in the list. Also, it is best to have much more proxies than processes running to scrape the site. This allows for faster scraping without getting a proxy blocked for 24 hours.
