#!/usr/bin/python3

'''
*
* Copyright (c) 2016
*      Politecnico di Torino.  All rights reserved.
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* For bug report and other information please write to:
* martino.trevisan@polito.it
*
*
'''


#Dependancies
# Install BrowserMob Proxy from https://bmp.lightbody.net/ in current directory
# sudo pip3 install selenium
# sudo pip3 install browsermob-proxy

import json
import sys
import random
import time
import argparse
import os
import subprocess
from browsermobproxy import Server
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from urllib.parse import urlparse
from real_thinking_time import random_thinking_time
import concurrent.futures




browser = "firefox"
timeout = 30
backoff = 0
save_headers=False
debug = 0

def main():
    
    global backoff
    global timeout
    global save_headers
    
    
    parser = argparse.ArgumentParser(description='Web Traffic Generator')
    parser.add_argument('in_file', metavar='input_file', type=str, nargs=1,
                       help='File where are stored the pages')                 
    parser.add_argument('out_dir', metavar='out_dir', type=str, nargs=1,
                       help='Output directory where HAR structures are saved') 
    parser.add_argument('har_export', metavar='har_export', type=str, nargs=1,
                       help='Path to Har Export extension xpi file.')                                    
    parser.add_argument('-b', '--backoff', metavar='max_backoff', type=int, nargs=1, default = [0],
                       help='Use real backoff with maximum value <max_backoff> seconds ')
    parser.add_argument('-t', '--timeout', metavar='timeout', type=int, nargs=1, default = [30],
                       help='Timeout in seconds after declaring failed a visit. Default is 30. Should be greater than max_backoff.')               
    parser.add_argument('-s','--start_page', metavar='start_page', type=int, nargs=1,
                       help='For internal usage, do not use')

    args = vars(parser.parse_args())


    # Parse agruments
    pages_file = args['in_file'][0]
    pages = open(pages_file,"r").read().splitlines() 
    out_dir = args['out_dir'][0]
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    timeout = args['timeout'][0]
    har_export=args["har_export"][0]

    backoff= args['backoff'][0]

    # Use last arguments to detect if i'm master or daemon
    if args["start_page"] is not None:
        daemon_start = args["start_page"][0]
    else:
        daemon_start = -1
    
    # If I'm the master
    if daemon_start == -1:
    

        # Execute the slave
        command = " ".join(sys.argv) + " -s 0"
        print ("Executing:", command ,  file=sys.stderr)
        ret = subprocess.call(command, shell=True)
        print("Quitted slave")
        
        # Keep execting untill all pages are requested
        while ret != 0:
            # Read last page requested, and restart
            start = int(open("/tmp/har_state", "r").read())
            print("Detected a Selenium block, restarting...",  file=sys.stderr)
            command = " ".join(sys.argv) + " -s " + str(start)
            print ("Executing:", command,  file=sys.stderr)
            ret = subprocess.call(command, shell=True)
        
        # End when all pages are requested
        print ("All pages requested",  file=sys.stderr)
        time.sleep(2)
        sys.exit(0)
        
    else: 
        
        # Start Selenium and Har Export


        profile  = webdriver.FirefoxProfile()

        profile.add_extension(har_export)
        
        # Set default NetExport preferences
        #profile.set_preference("devtools.netmonitor.har.enableAutoExportToFile", True)
        #profile.set_preference("devtools.netmonitor.har.forceExport", True)
        profile.set_preference("extensions.netmonitor.har.autoConnect", True)
        profile.set_preference("devtools.netmonitor.enabled", True);
        profile.set_preference("extensions.netmonitor.har.contentAPIToken", "test")
        #profile.set_preference("devtools.netmonitor.har.forceExport", "true")
        profile.set_preference("devtools.netmonitor.har.defaultLogDir", out_dir)
        profile.set_preference("devtools.netmonitor.har.includeResponseBodies", False)
        #profile.set_preference("devtools.netmonitor.har.pageLoadedTimeout", "2500")
 
        driver = webdriver.Firefox(firefox_profile=profile)
        time.sleep(1)
        
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
            future = executor.submit(request_url, page, driver)
            
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
        driver.quit()
        
        sys.exit(0)


def request_url(page, driver):
    
    try:       
        # Request the page
        url = page
        print("Requesting:", page)
        start_time = time.time()
        driver.get(url) 
        elapsed_time = time.time() - start_time

        if backoff != 0:   
            tm=random_thinking_time(backoff)
            print("Backoff", tm)
            time.sleep(tm)
        else:
            time.sleep(1)
        domain=url.split("/")[2]
        driver.execute_script(get_script(domain))  

    except Exception as e:
        print("Exception in page loading", e)
        while True:
            pass
        
def get_script(domain):
    script='var options = {token: "test", getData: true,  title: "my custom title", jsonp: false, fileName: "visit_%Y_%m_%d_%H_%M_%S_'+ domain.replace(".","_")\
    +'"};' + 'HAR.triggerExport(options).then(result => {console.log(result.data);});'

    return script
main()
