#!/usr/bin/python3
import json
from dateutil import parser
import operator
import datetime

import sys

input_har = json.load(open(sys.argv[1], "r"))


objects=[]
bytes=[]
tot_bytes=0
tot_obj=0

start_time=parser.parse(input_har["log"]["entries"][0]["startedDateTime"]).timestamp()

domain=input_har["log"]["pages"][0]["title"].split("/")[2]
on_load_time=input_har["log"]["pages"][0]["pageTimings"]["onLoad"]
DOM_load_time=input_har["log"]["pages"][0]["pageTimings"]["onContentLoad"]

for entry in input_har["log"]["entries"]:

    obj_start_time=parser.parse(entry["startedDateTime"]).timestamp()
    obj_delta_time= sum( [ v for v in entry["timings"].values() if v != -1])
    obj_time = obj_start_time - start_time + obj_delta_time/1000
    size = entry["response"]["bodySize"]
    objects.append( (obj_time, 1   ))
    bytes.append  ( (obj_time, size))
    tot_bytes+=size
    tot_obj+=1
    last_obj_time=obj_time



'''
#should return 4
tot_bytes=tot_obj=4
bytes=( (1,1),(3,1),(4,1),(8,1) ) 
objects=( (1,1),(3,1),(4,1),(8,1) )

objects=sorted(objects,key=operator.itemgetter(0))
bytes=sorted(bytes,key=operator.itemgetter(0))
'''

cumul_bytes=0
cumul_objects=0
for i in range (len(bytes)):
    time, size = bytes[i]
    bytes[i]   = (time, size/tot_bytes + cumul_bytes)
    objects[i] = (time, 1/tot_obj + cumul_objects)
    cumul_bytes=size/tot_bytes + cumul_bytes
    cumul_objects=1/tot_obj + cumul_objects

bytes = [(t, round(1-b,5)) for t,b in bytes]
objects = [(t, round(1-b,5)) for t,b in objects]


prec_score=1
prec_time=0
byte_index=0

for time, score in bytes:
    component=(time-prec_time)*prec_score
    byte_index+=component
    prec_score=score
    prec_time = time

prec_score=1
prec_time=0
object_index=0

for time, score in objects:
    component=(time-prec_time)*prec_score
    object_index+=component
    prec_score=score
    prec_time = time

print(domain, byte_index, object_index, on_load_time/1000, DOM_load_time/1000 )












