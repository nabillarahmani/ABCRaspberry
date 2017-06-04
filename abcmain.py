from flask import Flask
from flask import Response
from flask import redirect
from flask import render_template
from flask import render_template_string
from flask import session
from flask import stream_with_context
from flask import url_for
from flask_dotenv import DotEnv
from smartcard.System import readers
from beaker.middleware import SessionMiddleware
from smartcard.Exceptions import NoCardException
from smartcard.System import readers
from smartcard.util import toHexString
from binascii import unhexlify, b2a_base64
import time

app = Flask(__name__)
env = DotEnv()
env.init_app(app)
env.eval(keys={
	'DEBUG': bool,
	'TESTING': bool
})
app.logger.setLevel(app.config['LOG_LEVEL'])

url = './data/'

@app.route("/")
def index():
	import time
	import os
	"""
		Render the view of index page.
	"""
	write_data_to_file("is_at_index", 'data_exist')
	app.logger.debug('Accessing main page of raspberry application!')
	r = readers()
	reader = r[0]
	connection = reader.createConnection()
	while connection is not None:
		try:
			connection.connect()
			os.remove("is_at_index")
			return redirect(url_for('readcard'))
		except:
			continue	


def get_hex_string(array_of_hex, start, end):
	"""
	input	:
	return	: string representation of the given input
	"""
	hex_field_map_string = ""
	for x in array_of_hex:
		x = str(x)
		hex_field_map_string += x[2:]
	return hex_field_map_string[start:end]


def get_array_hex(array_of_dec):
	"""
	input	: receives input array of decimal from responds
	return	: return array of hex from the respond
	"""
	arr_hex = []
	for data in array_of_dec:
		arr_hex.append(hex(data))
	return arr_hex


def parse_field_map(hex_string):
	"""
	@input : get 
	@return: string of binary
	"""
	h_size = len(hex_string) * 4
	string_binary_field = (bin(int(hex_string, 16))[2:] ).zfill(h_size)
	return string_binary_field


def get_apdu_command(connection, APDU, offset_1, offset_2, length):
	APDU.append(offset_1)
	APDU.append(offset_2)
	APDU.append(length)
	result, sw1, sw2 = connection.transmit(APDU)
	return result, sw1, sw2


def select_apdu_command(connection, APDU):
	result, sw1, sw2 = connection.transmit(APDU)
	return result, sw1, sw2


def hexstring_to_decimal(hex_representation):
	"""
	@param : a number which contain 4 string hex_representation
	@return: a decimal which indicates a number of 4 digit hex representation
	"""
	return int("0x"+hex_representation, 16)


def change_offset(offset, addition):
	total_addition = int(offset) + int(addition)
	hex_representation = str(hex(total_addition)[2:]).zfill(4)
	first_offset = "0x"+hex_representation[:2]
	second_offset = "0x"+hex_representation[2:]
	first_offset = int(first_offset, 16)
	second_offset = int(second_offset, 16)
	return first_offset, second_offset


def get_total_length_map(length_map, start, end):
	total_length = 0
	i = 1
	length = "0"
	for data in length_map[start:end]:
		if i % 2  != 0:
			length = "0x" + length
			total_length += int(length, 16)
			# print("total_length now :{}".format(total_length))
			length = ""
		length += str(hex(data)[2:]).zfill(2)
		# print("length now: {}".format(length))
		i += 1
	total_length += int(length, 16)
	return total_length



@app.route("/readcard")
def readcard():
	import os
	"""
	Implementation of readcard using highlevel implementation
		
	"""
	app.logger.debug('Reading a smartcard!')
	write_data_to_file("is_at_readcard", 'data_exist')
	try:
		r = readers()
		print("Available readers:", r)

		reader = r[0]
		print ("Using:", reader)

		connection = reader.createConnection()
		connection.connect()

		# SELECT MF
		SELECT = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]

		data, sw1, sw2 = select_apdu_command(connection, SELECT)


		if sw1  == None and sw2 == None:
			# discard connection on card
			print("failed to render card")
			connection.disconnect()
			return redirect(url_for('index'))

		# Select DF
		APDU_DF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x10, 0x01]
		data, sw1, sw2 = select_apdu_command(connection, APDU_DF)

		# SELECT EF
		APDU_EF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0xFF]
		data, sw1, sw2 = select_apdu_command(connection, APDU_EF)


		APDU_GET = [0x00, 0xB0]
		# GET CARD TYPE
		data_card, sw1, sw2 = get_apdu_command(connection, APDU_GET, 0, 0, 2)


		# SELECT EF (FIELD MAP + LENGTH MAP)
		APDU_FIELD 		= [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x00]
		data, sw1, sw2 	= select_apdu_command(connection, APDU_FIELD)

		#Get field map + length map
		APDU_GET = [0x00, 0xB0]
		data, sw1, sw2 	= get_apdu_command(connection, APDU_GET, 0, 0, 51)

		flag_empty 		= True		
		
		# Check for each element whether it is filled yet or not
		for element in data:
			# IF there is one single element which not FF, then it is filled
			if element != '255':
				flag_empty = False

		if flag_empty == True:
			connection.disconnect()
			write_data_to_file("is_empty_card", 'data_exist')
			time.sleep(5)
			os.remove("is_empty_card")
			app.logger.debug('Card is empty!')
			return redirect(url_for('index'))

		if data_card[1] != 2:
			connection.disconnect()
			write_data_to_file("is_not_xirka", 'data_exist')
			time.sleep(5)
			os.remove("is_not_xirka")
			app.logger.debug('Card profile is not Xirka!')
			return redirect(url_for('index'))

		# get the hex representation of respond
		# parse the first 3 bits from the respond to check the length
		# Field map = 10101010100011 (in binary) contains 3 bytes of binary representation
		# print "data : {}\n".format(data)
		respond_field_map 	= get_array_hex(data)

		field_map 			= parse_field_map(get_hex_string(respond_field_map, 0, 6))

		# Get the total length map of data 1
		length_map = data[3:]

		total_length_data_1 = get_total_length_map(length_map, 0, 18)

		# SELECT EF FOR FIRST DATA 
		APDU_SELECT_DATA_1 = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x01]
		data, sw1, sw2 = select_apdu_command(connection, APDU_SELECT_DATA_1)			

		# handle if content inside card is null
		if sw1 == None and sw2 == None:
			#sdcard disconnect
			connection.disconnect()
			app.logger.debug('The content inside card is null')


		app.logger.debug('Reading the first segment of data!')
		iteration = total_length_data_1 / 252
		remainder = total_length_data_1 % 252
		APDU_GET = [0x00, 0xB0]
		respond_data_1	= []

		if total_length_data_1 < 252:
			respond_data_1, sw1, sw2 = get_apdu_command(connection, APDU_GET, 0, 0, total_length_data_1)
		else:
			offset_1 = 0
			offset_2 = 0
			while iteration > 0:
				APDU_GET = [0x00, 0xB0]
				data, sw1, sw2 = get_apdu_command(connection, APDU_GET, offset_1, offset_2, 252)
				total_offset = get_total_length_map([offset_1,offset_2], 0, 2)
				offset_1, offset_2 = change_offset(total_offset, 252)
				respond_data_photo.extend(data)
				iteration -= 1
			if remainder != 0:
				APDU_GET = [0x00, 0xB0]
				data, sw1, sw2 = get_apdu_command(connection, APDU_GET, offset_1, offset_2, remainder)
				respond_data_1.extend(data)


		# initialize the length of variable needed
		length_identification_number_start 	= 0
		length_identification_number_end 	= 0
		length_full_name_start 				= 0
		length_full_name_end 				= 0
		length_photo_start					= 0
		length_photo_end					= 0
		length_fingerprint_start			= 0
		length_fingerprint_end				= 0 

		# Iterate the length map to get the start and end of each data
		i = 0
		start_offset = 0
		# Getting the start and end index of length
		for data in length_map:
			start_offset += data
			if i >= 4 and i <= 5:
				if i == 4:
					length_identification_number_start = start_offset
					length_identification_number_end = start_offset
				length_identification_number_end += data
			
			if i >= 6 and i <= 7:
				if i == 6:
					length_full_name_start = start_offset
					length_full_name_end = start_offset
				length_full_name_end += data
			i += 1

		respond_mapped = {'identification_number': '', 'full_name': '', 'fingerprint' : '', 'photo' : ''}
		# check if each mapped data is exist
		# print(field_map)
		# print(field_map[2] == "1")
		# Get data for identification number
		if field_map[2] == "1":
			for data in respond_data_1[length_identification_number_start:length_identification_number_end]:
				respond_mapped['identification_number'] += str(chr(data))
		else:
			#It means there's no identification number!
			connection.disconnect()
			write_data_to_file("is_empty_identification_number", 'data_exist')
			time.sleep(5)
			os.remove("is_empty_identification_number")
			app.logger.debug('Card doesnt have identification number!')
			return redirect(url_for('index'))
		# Get data for fullname
		if field_map[3] == "1":
			for data in respond_data_1[length_full_name_start:length_full_name_end]:
				respond_mapped['full_name'] += str(chr(data))

		app.logger.debug('Reading photo from smartcard')
		photo = ""
		respond_data_photo = []
		# Get data for data photo
		if field_map[11] == "1":
			total_length_data_photo = get_total_length_map(length_map, 22, 24)
			APDU_SELECT_PHOTO = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x04]
			data, sw1, sw2 = connection.transmit(APDU_SELECT_PHOTO)
			iteration = total_length_data_photo / 252
			remainder = total_length_data_photo % 252
			APDU_GET = [0x00, 0xB0]
			
			if total_length_data_photo < 252:
				respond_data_photo, sw1, sw2 = get_apdu_command(connection, APDU_GET, 0, 0, total_length_data_photo)
			else:
				offset_1 = 0
				offset_2 = 0
				while iteration > 0:
					APDU_GET = [0x00, 0xB0]
					data, sw1, sw2 = get_apdu_command(connection, APDU_GET, offset_1, offset_2, 252)
					total_offset = get_total_length_map([offset_1, offset_2], 0, 2)
					offset_1, offset_2 = change_offset(total_offset, 252)
					respond_data_photo.extend(data)
					iteration -= 1
				if remainder != 0:
					APDU_GET = [0x00, 0xB0]
					data, sw1, sw2 = get_apdu_command(connection, APDU_GET, offset_1, offset_2, remainder)
					respond_data_photo.extend(data)

			for data in respond_data_photo:
				photo += str(chr(data))
			respond_mapped['photo'] = photo
			
		app.logger.debug('Reading data fingerprint from smartcard...')
		fingerprint = ""
		respond_data_fingerprint = []
		if field_map[12] == "1":
			total_length_data_fingerprint = get_total_length_map(length_map, 24, 26)
			APDU_SELECT_FINGERPRINT = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x05]
			data, sw1, sw2 = connection.transmit(APDU_SELECT_FINGERPRINT)
			iteration = total_length_data_fingerprint / 252
			remainder = total_length_data_fingerprint % 252
			APDU_GET_FINGERPRINT = [0x00, 0xB0]

			if total_length_data_fingerprint < 252:
				respond_data_fingerprint, sw1, sw2 = get_apdu_command(connection, APDU_GET, 0, 0, total_length_data_fingerprint)
			else:
				offset_1 = 0
				offset_2 = 0
				while iteration > 0:
					APDU_GET = [0x00, 0xB0]
					data, sw1, sw2 = get_apdu_command(connection, APDU_GET, offset_1, offset_2, 252)
					total_offset = get_total_length_map([offset_1, offset_2], 0, 2)
					offset_1, offset_2 = change_offset(total_offset, 252)
					respond_data_fingerprint.extend(data)
					iteration -= 1
				if remainder != 0:
					APDU_GET = [0x00, 0xB0]
					data, sw1, sw2 = get_apdu_command(connection, APDU_GET, offset_1, offset_2, remainder)
					respond_data_fingerprint.extend(data)

			for data in respond_data_fingerprint:
				fingerprint += str(chr(data))
			respond_mapped['fingerprint'] = fingerprint

		if photo is not '':
			write_data_to_file(url+'photo_taken', photo)	

		if fingerprint is not '':
			write_data_to_file(url+'/fingerprint_taken', fingerprint)

		# Write the data so that it would be sufficient to access it later!
		fullname = respond_mapped['full_name']
		identification_number = respond_mapped['identification_number']
		t = open(url+'information_taken.txt', "w+")
		t.write("identification_number:{}\n".format(identification_number))
		t.write("fullname:{}".format(fullname))
		t.close()
		return redirect(url_for('readfingerprint'))
	except Exception as e:
		app.logger.debug(str(e))
		write_data_to_file("is_error_card", 'data_exist')
		time.sleep(5)
		os.remove("is_error_card")
		return redirect(url_for('index'))



def get_data_from_file(data):
	"""
		This method will read the binary data from binary file
		@param : any relative path to desired file
		@return: a binary data which represent the given data
	"""
	f = open(data)
	data = f.read()
	f.close()
	return data


def write_data_to_file(path, data):
	f = open(path, 'w+')
	f.write(data)
	f.close()


def verification_document(extract_fingerprint, extract_fingerprint_smartcard):
	"""
		This will match between the data_readcarda on smart card and on the given fingerprint
	"""
	return True


def verification_cekal(identification_number):
	import requests
	"""
		This method will send a GET request into the API and retrieve cekal status
	"""
	app.logger.debug('Getting status cekal with corresponded identification number')
	result = False
	try:
		data = {'identification_number' : identification_number}
		r = requests.get('http://webservice-abcsystem.herokuapp.com/get_cekal/', params=data)
		app.logger.debug('now accessing {}'.format(r.url))
		if r.status_code == 200:
			app.logger.debug('Succeed on getting status cekal')
		else:
			app.logger.debug('There is no data on this user')
		app.logger.debug("Request result : {}".format(r.text))
		if r.text == 'False':
			result = False
		else:
			result = True
		return result 
	except:
		app.logger.debug('Failed on making request')
		return result	


@app.route("/readfingerprint")
def readfingerprint():
	"""
		This method will extract the fingerprint from the fingerprint reader
		It will store the fingerprint extract onto session and pass it into verification_process
		This method is not implemented yet
	"""
	app.logger.debug('Accessing the readfingerprint route...')
	return redirect(url_for('verification_process'))


@app.route("/verification_process")
def verification_process():
	import os.path
	"""
		This method will check the verification process between person to document
		This method will also check to server cekal
	"""
	app.logger.debug('Accessing the verification process now...')
	url = './data/'
	# Get the fingerprint data
	fingerprint_extract = ''
	if os.path.isfile(url + 'fingerprint'):
		fingerprint_extract = get_data_from_file(url + 'fingerprint')
	else:
		# do nothing because the implementation will be implemented soon
		pass

	smartcard_extract = {}
	# Get the identification number and fullname data from the
	# file information_taken.txt 
	if os.path.isfile(url +'information_taken.txt'):
		datas = get_data_from_file(url + 'information_taken.txt')
		datas = datas.split("\n")
		for data in datas:
			smartcard_extract[data.split(':')[0]] = data.split(':')[1]
			session[data.split(':')[0]] = data.split(':')[1]
	else:
		# show error there's no data in smartcard session
		pass

	# Get the data for photo taken
	photo_taken = ''
	if os.path.isfile(url + 'photo_taken'):
		photo_taken = get_data_from_file(url + 'photo_taken')
	else:
		# show error
		pass 
	smartcard_extract['photo_taken'] = photo_taken

	fingerprint_taken = ''
	photo_taken = ''
	if os.path.isfile(url + 'fingerprint_taken'):
		fingerprint_taken = get_data_from_file(url + 'fingerprint_taken')
	else:
		# show error
		pass
	smartcard_extract['fingerprint_taken'] = fingerprint_taken

	print("smartcard_extract : {}".format(smartcard_extract))

	# Check the whether the fingerprint taken is match with fingerprint data
	fingerprint_extract_smartcard = smartcard_extract['fingerprint_taken']
	result_fingerprint = verification_document(fingerprint_extract, fingerprint_extract_smartcard)

	status_cekal = False
	session['verifikasi_fingerprint'] = result_fingerprint
	if result_fingerprint:
		#if succeeed then call the API
		# Asumsikan API selalu menyala
		if smartcard_extract['identification_number'] is not None:
			status_cekal = verification_cekal(smartcard_extract['identification_number'])
			session['status_cekal'] = status_cekal
		else:
			render_template('failed_identification_number.html')
	else:
		#show fingerprint not match!
		render_template('failed_fingerprint_verification.html')
	
	app.logger.debug('The fingerprint verif : {} and status_cekal verif : {}'.format(result_fingerprint, status_cekal))
	if result_fingerprint and not status_cekal:
		write_data_to_file("succeed_verification", 'data_exist')
		time.sleep(5)
		os.remove("succeed_verification")	
	else:
		write_data_to_file("failed_verification", 'data_exist')
		time.sleep(5)
		os.remove("failed_verification")
			
	return redirect(url_for('get_camera_data'))


def take_image():
	import os
	import time
	import datetime 
	"""
		This method will take the picture of the traveller
	"""
	ts = time.time()
	ts = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H:%M:%S')
	app.logger.debug('Taking picture now! Say cheese!!')
 	os.system("sudo fswebcam --fps 15 -S 20 -s brightness=80% -r 100x100 --no-banner -q ./data_logging/"+ts+".jpeg")
 	return 


@app.route("/logging")
def logging():
	import os, os.path
	import requests
	import datetime
	import time
	"""
		This method will do the logging
	"""
	app.logger.debug('Accessing logging route')
	data_logging = {'identification_number': '', 'full_name': '', 'photo_taken' : '', 'status_verification_cekal' : False, 'status_verification_fingerprint': False}
	
	if 'identification_number' in session:
		data_logging['identification_number'] = session['identification_number']
	if 'fullname' in session:
		data_logging['fullname'] = session['fullname']
	if 'status_cekal' in session:
		data_logging['status_verification_cekal'] = session['status_cekal']
	if 'verifikasi_fingerprint' in session:
		data_logging['status_verification_fingerprint'] = session['verifikasi_fingerprint']
	# Get current timestamp
	ts = time.time()
	ts = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
	data_logging['timestamp_traveller'] = ts
	app.logger.debug('ready to send request this : {}'.format(data_logging))
	try:
		result = requests.post("http://webservice-abcsystem.herokuapp.com/logging_data", params=data_logging)
		app.logger.debug(result.url)
		if result.status_code == 200:
			app.logger.debug('SUCCEED SEND DATA LOGGING')
		else:
			app.logger.debug('FAILED ON LOGGING')
		return redirect(url_for('closing_connection'))
	except Exception as e:
		app.logger.debug(str(e))
		return redirect(url_for('closing_connection'))


@app.route("/closing_connection")
def closing_connection():
	import time
	import os, shutil, os.path
	"""
		This method will ask the user the reject the card!
	"""
	# Destroy session for next use!
	session.clear()
	# Destroy all files within data directory!
	folder = 'data/'
	for the_file in os.listdir(folder):
		file_path = os.path.join(folder, the_file)
		try:
			if os.path.isfile(file_path):
			    os.unlink(file_path)
				#elif os.path.isdir(file_path): shutil.rmtree(file_path)
		except Exception as e:
			print(e)
	# Write file is_exist_card for an ajax to check it
	write_data_to_file("is_exist_card", 'data_exist')
	r = readers()
	reader = r[0]
	connection = reader.createConnection()
	connection.disconnect()
	time.sleep(10) # delays for 5 seconds
	os.remove('is_exist_card')
	return redirect(url_for('index'))


@app.route("/get_camera_data")
def get_camera_data():
	"""
		This method will captured the traveller photo and store it into logging folder
	"""	
	app.logger.debug('accessing /get_camera_data')
	take_image()
	# If verification succeed
	if session['verifikasi_fingerprint'] and not session['status_cekal']:
		return redirect(url_for('open_gate'))		
	else:
		return redirect(url_for('logging'))


@app.route("/open_gate")
def open_gate():
	import RPi.GPIO as GPIO
	"""
		This method will switch the gate, so that the traveller can pass the gate
	"""
	# setting a current mode
	GPIO.setmode(GPIO.BCM)
	#removing the warings 
	GPIO.setwarnings(False)
	#creating a list (array) with the number of GPIO's that we use 
	pin = 18 
	#setting the mode for all pins so all will be switched on 
	GPIO.setup(pin, GPIO.OUT)
	GPIO.output(pin,  GPIO.HIGH)
	time.sleep(1)
	GPIO.output(pin, GPIO.LOW)
	#cleaning all GPIO's 
	GPIO.cleanup()
	return redirect_url(url_for('logging'))


@app.errorhandler(404)
def page_not_found_error(err):
	"""
	Render the view of error 404 page
	"""
	return render_template('404.html', title='Page not found', current_page='404')


@app.errorhandler(500)
def internal_server_error(err):
	"""
	Render the view of error 500 page
	"""
	return render_template('500.html', title='Server internal server error', current_page='500')


if __name__ == "__main__":
	# app.wsgi_app = SessionMiddleware(app.wsgi_app, session_opts)
	app.secret_key = 'ansdjsakd12n3kj1'
	app.run(host=app.config['HOST'], port=int(app.config['PORT']))