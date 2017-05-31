# import os

# url = 'data/'
# data = ''
# if os.path.isfile(url +'information_taken.txt'):
# 	f = open(url +'information_taken.txt')
# 	data = f.read()
# 	f.close

# print(data)
# print(data.split("\n"))
# smartcard_extract = {}
# for data in data.split("\n"):
# 	smartcard_extract[data.split(': ')[0]] = data.split(': ')[1]
# print(smartcard_extract)

import os, os.path
import datetime
import time
"""
	This method will do the logging
"""
# TODO IMPLEMENT LOGGING INTO THE SERVER LOGGING
data_logging = {'identification_number': '', 'full_name': '', 'photo_taken' : '', 'status_cekal' : False}

if 'identification_number' in session:
	data_logging['identification_number'] = session['identification_number']
if 'fullname' in session:
	data_logging['fullname'] = session['fullname']
# Get the data for status cekal
if 'status_cekal' in session:
	data_logging['status_cekal'] = session['status_cekal']
# Get the data for photo traveller
photo_taken = ''
if os.path.isfile(url + 'traveller.jpg'):
	photo_taken = get_data_from_file(url + 'traveller.jpg')
else:
	# show error
	pass 
data_logging['photo_taken'] = photo_taken

# Get current timestamp
ts = time.time()
ts = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
data_logging['timestamp_traveller'] = ts

print(data_logging)