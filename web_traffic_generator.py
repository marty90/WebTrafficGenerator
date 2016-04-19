#!/usr/bin/python3

#Dependancies
# Install BrowserMob Proxy from https://bmp.lightbody.net/ in current directory
# sudo pip3 install selenium
# sudo pip3 install browsermob-proxy

import json
import sys
import random
import time
import os
import subprocess
from browsermobproxy import Server
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from urllib.parse import urlparse
import concurrent.futures

browser = "firefox"
browser_mob_proxy_location=os.environ["BROWSERMOBPROXY_BIN"]
timeout = 10
debug = 0

def main():
    
    
    # Check command line
    if len(sys.argv) < 3:
        print("Wrong arguments... Quitting...",  file=sys.stderr)
        print("Usage: web_traffic_generator.py <page_file> <output_file>")
        exit()

    # Parse agruments
    pages_file = sys.argv[1]
    pages = open(pages_file,"r").read().splitlines() 
    out_file = sys.argv[2]

    # Use last arguments to detect if i'm master or daemon
    if len(sys.argv) > 3:
        daemon_start = int (sys.argv[3])
    else:
        daemon_start = -1
    
    # If I'm the master
    if daemon_start == -1:
    
        # Create empty outfile
        with open(out_file, "w") as f:
            pass
        
        # Execute the slave
        command = " ".join(sys.argv) + " 0"
        print ("Executing:", command ,  file=sys.stderr)
        ret = subprocess.call(command, shell=True)
        print("Quitted slave")
        
        # Keep execting untill all pages are requested
        while ret != 0:
            # Read last page requested, and restart
            start = int(open("/tmp/har_state", "r").read())
            print("Detected a Selenium block, restarting...",  file=sys.stderr)
            command = " ".join(sys.argv) + " " + str(start)
            print ("Executing:", command,  file=sys.stderr)
            ret = subprocess.call(command, shell=True)
        
        # End when all pages are requested
        print ("All pages requested",  file=sys.stderr)
        sys.exit(0)
        
    else: 
        
        # Start Selenium and Proxy
        server = Server(browser_mob_proxy_location)
        server.start()
        proxy = server.create_proxy()
        profile  = webdriver.FirefoxProfile()
        profile.set_proxy(proxy.selenium_proxy())
        driver = webdriver.Firefox(firefox_profile=profile)
        
        # Start requesting pages from the last one
        pages = pages[daemon_start:]
        n = daemon_start
        
        # Create a thread pool
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Start requesting pages
        for page in pages:
            if debug > 0:
                print("Requesting:", n , page,  file=sys.stderr)
            
            # Submit the future
            future = executor.submit(request_url, page, driver, proxy, out_file)
            
            # Wait to complete
            t = 0
            while True:
                time.sleep(1)
                if debug > 1:
                    print("Timeout", t,  file=sys.stderr)
                if future.done():
                    break
                t+=1
                
                # If timeout elapses, a block happened
                if t >= timeout:
                
                    # Try all the ways to stop everything
                    open("/tmp/har_state", "w").write(str(n+1))
                    # Stop Selenium
                    try:
                        server.stop()
                        driver.quit()
                    except:
                        pass
                    # Kill the browser    
                    try:
                        command = "killall " + browser
                        subprocess.call(command, shell=True)
                        subprocess.call(command + " -KILL", shell=True) 
                    except:
                        pass
                        
                    if debug > 1:
                        print ("Quitting with errcode:", n+1,file=sys.stderr)
                    future.cancel()
                    print("Quitting slave",  file=sys.stderr)
                    
                    # Suicide
                    os.system('kill %d' % os.getpid())

            n+=1

        # If all pages requested, exit with '0' status
        server.stop()
        driver.quit()
        
        sys.exit(0)


def request_url(page, driver, proxy, out_file):
    
    try:

        # Open outfile in append mode 
        f = open (out_file, "a")
        proxy.new_har("Har")
        # Request the page
        url = page
        driver.get(url) 
        tmp_diz={"actual_url" : url }
        tmp_diz.update(proxy.har)
        f.write(json.dumps(tmp_diz) + "\n")
            
    except Exception as e:
        print("Exception in page loading", e)
        while True:
            pass
        

main()
