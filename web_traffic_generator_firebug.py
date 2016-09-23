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
* To download NetExport:
*     wget https://getfirebug.com/releases/netexport/netExport-0.9b7.xpi
* To download FireBug:
*     wget https://addons.cdn.mozilla.net/user-media/addons/1843/firebug-2.0.17-fx.xpi?filehash=sha256%3A32a1eef23bdac7bb97a06b527f5c88fe94476755f76b8b1db3b3c66acddd83da
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
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from urllib.parse import urlparse
import concurrent.futures

sys.path.append(os.path.dirname(__file__))
from real_thinking_time import random_thinking_time




disp_width = 800
disp_height = 600
browser = "firefox"
timeout = 60
real_backoff = 0
static_backoff = 0
debug = 0
out_dir=""

def main():
    
    global real_backoff
    global static_backoff
    global timeout
    global out_dir
    
    parser = argparse.ArgumentParser(description='Web Traffic Generator')
    parser.add_argument('in_file', metavar='input_file', type=str, nargs=1,
                       help='File where are stored the pages')                 
    parser.add_argument('out_dir', metavar='out_dir', type=str, nargs=1,
                       help='Output directory where HAR structures are saved')                                    
    parser.add_argument('-r', '--real_backoff', metavar='real_backoff', type=int, nargs=1, default = [0],
                       help='Use real backoff distribution with maximum value <real_backoff> seconds ')
    parser.add_argument('-b', '--static_backoff', metavar='static_backoff', type=int, nargs=1, default = [1],
                       help='Use a static backoff with value <static_backoff> seconds ')
    parser.add_argument('-t', '--timeout', metavar='timeout', type=int, nargs=1, default = [30],
                       help='Timeout in seconds after declaring failed a visit. Default is 30.')  
    parser.add_argument('-v','--virtual_display', metavar='virtual_display', default=False, action='store_const', const=True,
                       help='Use a virtual display instead of the physical one')
                                                                       
    parser.add_argument('-s','--start_page', metavar='start_page', type=int, nargs=1,
                       help='For internal usage, do not use')

    args = vars(parser.parse_args())


    # Parse arguments
    pages_file = args['in_file'][0]
    pages = open(pages_file,"r").read().splitlines() 
    out_dir = args['out_dir'][0]
    if not out_dir[0] == "/":
        out_dir=os.getcwd() + "/" + out_dir  
    
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)



    real_backoff   = args['real_backoff']  [0]
    static_backoff = args['static_backoff'][0]
    timeout = args['timeout'][0] + real_backoff + static_backoff
    virtual_display = args['virtual_display']
    

    if virtual_display:
        from pyvirtualdisplay import Display

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
        

        profile  = webdriver.FirefoxProfile()

        profile.add_extension(os.path.dirname(__file__) + "/" + "netExport-0.9b7.xpi")
        profile.add_extension(os.path.dirname(__file__) + "/" + "firebug-2.0.17-fx.xpi")
        

        # Set default Firefox preferences
        profile.set_preference("app.update.enabled", False)

        domain = "extensions.firebug."

        # Set default Firebug preferences
        profile.set_preference(domain + "currentVersion", "1.9.2")
        profile.set_preference(domain + "allPagesActivation", "on")
        profile.set_preference(domain + "defaultPanelName", "net")
        profile.set_preference(domain + "net.enableSites", True)

        # Set default NetExport preferences
        profile.set_preference(domain + "netexport.alwaysEnableAutoExport", True)
        profile.set_preference(domain + "netexport.showPreview", False)
        profile.set_preference(domain + "netexport.defaultLogDir", out_dir)
        profile.set_preference(domain + "extensions.firebug.netexport.timeout", max(timeout-5,5) )
        profile.set_preference(domain + "extensions.firebug.netexport.includeResponseBodies", False)
 
        # Start a virtual display if required
        if virtual_display:
            display = Display(visible=0, size=(disp_width, disp_height))
            display.start()
            
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
        driver.get("about:blank")
        driver.quit()
        
        sys.exit(0)


def request_url(page, driver):
    
    try:       
        # Request the page
        url = page
        print("Requesting:", page)
        start_time = time.time()
        driver.get(url) 
        end_time=time.time()
        elapsed_time = end_time - start_time

        #domain=url.split("/")[2]
        #driver.execute_script(get_script(domain,page,elapsed_time))  
        
        if real_backoff != 0:   
            tm=random_thinking_time(real_backoff)
        else:
            tm=static_backoff
        print ("Pause:", tm)
        time.sleep(tm)





    except Exception as e:
        print("Exception in page loading", e)
        while True:
            pass
        
def get_script(domain,page,elapsed_time):
    script='\
    function triggerExport() {\
        var options = {\
            token: "test", \
            getData: true,  \
            title: "' + str(elapsed_time) + " " + page +'", \
            jsonp: false,\
            fileName: "visit_%Y_%m_%d_%H_%M_%S_'+ domain.replace(".","_") +'"};' + \
        'HAR.triggerExport(options).then(result => {console.log(result.data);});};\
    if (typeof HAR === "undefined") {\
        addEventListener("har-api-ready", triggerExport, false);\
    } else {\
        triggerExport();\
    };'

    return script
    
main()
