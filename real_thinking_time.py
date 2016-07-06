#!/usr/bin/python3

import numpy as np
import os
from scipy.interpolate import interp1d
import random

input_file="real_thinking_time_points"

x = [ float(row.split()[0])  for row in open (os.path.dirname(__file__)+ "/" + input_file, "r") ]
y = [ float(row.split()[1])  for row in open (os.path.dirname(__file__)+ "/" +  input_file, "r") ]

f = interp1d(x, y)

def random_thinking_time(max_value=300):

    time = float(f(random.random()))/1000000
    if time > max_value:
        return max_value
    else:
        return time



