from flask import Flask
from flask import Response
from flask import redirect
from flask import render_template
from flask import render_template_string
from flask import request
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

@app.route("/")
def index():
	import time
	"""
		Render the view of index page.
	"""
	r = readers()
	reader = r[0]
	connection = reader.createConnection()
	while connection is not None:
		try:
			connection.connect()
			return redirect(url_for('readcard'))
		except:
			continue	
	# render_template('index.html', title='', current_page='ABC Gate Home')


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


# Implementation of readcard using highlevel implementation
@app.route("/readcard")
def readcard():
	import base64
	"""
		
	"""
	try:
		r = readers()
		# print("Available readers:", r)

		reader = r[0]
		# print ("Using:", reader)

		connection = reader.createConnection()
		connection.connect()

		# SELECT MF
		SELECT = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]

		data, sw1, sw2 = connection.transmit(SELECT)


		if sw1  == None and sw2 == None:
			# discard connection on card
			# print("failed to render card")
			pass

		# Select DF
		APDU_DF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x10, 0x01]
		data, sw1, sw2 = connection.transmit(APDU_DF)

		# SELECT EF
		APDU_EF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0xFF]
		data, sw1, sw2 = connection.transmit(APDU_EF)

		# GET CARD TYPE
		APDU_CARD = [0x00, 0xB0, 0x00, 0x00, 0x02]
		data, sw1, sw2 = connection.transmit(APDU_CARD)

		# SELECT EF (FIELD MAP + LENGTH MAP)
		APDU_FIELD 		= [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x00]
		data, sw1, sw2 	= connection.transmit(APDU_FIELD)

		#Get field map + length map
		APDU_GET_FIELD 	= [0x00, 0xB0, 0x00, 0x00, 0x33]
		data, sw1, sw2 	= connection.transmit(APDU_GET_FIELD)
		flag_empty 		= True	
		
		# Check for each element whether it is filled yet or not
		for element in data:
			# IF there is one single element which not FF, then it is filled
			if element != '255':
				flag_empty = False

		if flag_empty == True:
			#sdcard disconnect
			# print("error")
			pass

		# get the hex representation of respond
		# parse the first 3 bits from the respond to check the length
		# Field map = 10101010100011 (in binary) contains 3 bytes of binary representation
		respond_field_map 	= get_array_hex(data)
		# print(respond_field_map)

		field_map 			= parse_field_map(get_hex_string(respond_field_map, 0, 6))
		print("field map:")
		print(field_map)

		# Get the total length of map
		total_length_map= 0
		length_map 		= data[3:]
		print("length map:")
		print(length_map)
		print(data)
		for x in length_map:
			total_length_map += x

		# print(total_length_map)

		# SELECT EF FOR FIRST DATA 
		APDU_SELECT_DATA_1 = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x01]
		data, sw1, sw2 = connection.transmit(APDU_SELECT_DATA_1)			

		# handle if content inside card is null
		if sw1 == None and sw2 == None:
			#sdcard disconnect
			pass
			# print('error')

		iteration 		= total_length_map / 240
		APDU_GET_DATA_1	= [0x00, 0xB0, 0x00, 0x00]
		respond_data_1	= []

		if total_length_map < 240:
			APDU_GET_DATA_1.append(total_length_map)
			respond_data_1, sw1, sw2 = connection.transmit(APDU_GET_DATA_1)	
		else:
			while iteration >= 0:
				if (total_length_map - 240) > 0 :
					# By default take 240 bytes from the card
					APDU_GET_DATA_1.append(240)
					data, sw1, sw2 = connection.transmit(APDU_GET_DATA_1)
					if sw1 == None and sw2 == None:
						pass
						#sdcard disconnect
						# print('error')
					respond_data_1.extend(data)
					APDU_GET_DATA_1.pop()
					iteration -= 1
				else:
					# If smaller than the threshold then, take the remainder
					remainder = total_length_map - 240
					APDU_GET_DATA_1.append(remainder)
					data, sw1, sw2 = connection.transmit(APDU_GET_DATA_1)
					if sw1 == None and sw2 == None:
						pass
						#sdcard disconnect
						# print('error')
					respond_data_1.extend(data)
					APDU_GET_DATA_1.pop()
					iteration -= 1

		# initialize the length of variable needed
		length_identification_number_start 	= 0
		length_identification_number_end 	= 0
		length_full_name_start 				= 0
		length_full_name_end 				= 0
		length_icao_2_start					= 0
		length_icao_2_end					= 0
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

			if i>= 20 and i <= 21:
				if i == 20:
					length_icao_2_start = start_offset
					length_icao_2_end = start_offset
				length_icao_2_end += data

			if i >= 22 and i <= 23:
				if i == 22:
					length_photo_start = start_offset
					length_photo_end = start_offset
				length_photo_end += data
			if i >= 24 and i <= 25:
				if i == 24:
					length_fingerprint_start = start_offset
					length_fingerprint_end = start_offset
				length_fingerprint_end += data
			i += 1

		respond_mapped = {'identification_number': '', 'full_name': '', 'icao_2' : '', 'photo':'', 'fingerprint':''}
		
		# check if each mapped data is exist
		# Get data for identification number
		if field_map[2] == "1":
			for data in respond_data_1[length_identification_number_start:length_identification_number_end]:
				respond_mapped['identification_number'] += str(chr(data))
		# Get data for fullname
		if field_map[3] == "1":
			for data in respond_data_1[length_full_name_start:length_full_name_end]:
				respond_mapped['full_name'] += str(chr(data))

		# Get data for data ICAO 2
		if field_map[10] == "1":
			APDU_SELECT_ICAO_2 = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x03]
			data, sw1, sw2 = connection.transmit(APDU_SELECT_ICAO_2)
			
			APDU_GET_ICAO_2 = [0x00, 0xB0, 0x00, 0x00]
			APDU_GET_ICAO_2.extend(length_icao_2_end - length_icao_2_start)

			data_icao, sw1, sw2 = connection.transmit(APDU_GET_ICAO_2)

			for data in data_icao:
				respond_mapped['icao_2'] += str(chr(data))

		photo = ""
		# Get data for data photo
		if field_map[11] == "1":
			APDU_SELECT_PHOTO = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x04]
			data, sw1, sw2 = connection.transmit(APDU_SELECT_PHOTO)
			length_byte = length_photo_end - length_photo_start
			APDU_GET_PHOTO = [0x00, 0xB0, 0x00, 0x00]
			APDU_GET_PHOTO.append(length_byte)

			data_photo, sw1, sw2 = connection.transmit(APDU_GET_PHOTO)
			# print(data_photo)
			for data in data_photo:
				# do base64 encode to get the photo data
				hex_string = hex(data)[2:].zfill(2)
				photo += hex_string
			
			respond_mapped['photo'] = photo
			

		fingerprint = ""	
		if field_map[12] == "1":
			APDU_SELECT_FINGERPRINT = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x05]
			data, sw1, sw2 = connection.transmit(APDU_SELECT_FINGERPRINT)
			length_byte = length_fingerprint_end - length_fingerprint_start
			APDU_GET_FINGERPRINT = [0x00, 0xB0, 0x00, 0x00]
			APDU_GET_PHOTO.append(length_byte)

			data_fingerprint = connection.transmit(APDU_GET_FINGERPRINT)

			for data in data_fingerprint:
				hex_string = hex(data)[2:].zfill(2)
				fingerprint += hex_string

			respond_mapped['fingerprint'] = fingerprint
		
		# Store the value into session
		if not 'data_readcard' in session:
			session['data_readcard'] = respond_mapped
		else:
			# Destroy the session and make a new one!
			# Do implement destroy the session
			session['data_readcard'] = respond_mapped
			pass

		return redirect(url_for('readfingerprint'))
	except Exception as e:
		return e


def get_picture(image):



def verification_document(extract_fingerprint, extract_fingerprint_smartcard):
	import face_recognition
	"""
		This will match between the data on smart card and on the given fingerprint
	"""
	real_fingerprint = get_picture("dummy.jpg")
	card_fingerprint = get_picture(extract_fingerprint_smartcard)

	known_image = face_recognition.load_image_file(real_fingerprint)
	unknown_image = face_recognition.load_image_file(card_fingerprint)

	biden_encoding = face_recognition.face_encodings(known_image)[0]
	unknown_encoding = face_recognition.face_encodings(unknown_image)[0]

	results = face_recognition.compare_faces([biden_encoding], unknown_encoding)

	return results[0]


def verification_cekal(identification_number):
	"""
		This method will send a GET request into the API and retrieve cekal status
	"""
	return True
	


@app.route("/readfingerprint")
def readfingerprint():
	"""
		This method will extract the fingerprint from the fingerprint reader
		It will store the fingerprint extract onto session and pass it into verification_process
	"""
	session['data_fingerprint'] = 'sudah_ada'
	return redirect(url_for('verification_process'))


@app.route("/verification_process")
def verification_process():
	"""
		This method will check the verification process between person to document
		This method will also check to server cekal
	"""
	# Get the finger
	fingerprint_extract = ''
	if 'data_fingerprint' in session:
		fingerprint_extract = session['data_fingerprint']
	else:
		# show error there's no data in smartcard session
		pass
	
	smartcard_extract = {}
	if 'data_readcard' in session:
		smartcard_extract = session['data_readcard']
	else:
		# show error there's no data in smartcard session
		pass

	fingerprint_extract_smartcard = smartcard_extract['fingerprint']
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
	
	if result_fingerprint and status_cekal:
		render_template('succeed_verification.html')	
	else:
		render_template('failed_verification.html')
		
	return redirect(url_for('get_camera_data'))


def take_image():
	import os
	import time
	"""
		This method will take the picture of the traveller
	"""
	waktu = time.strftime("%Y-%m-%d") + "_" + time.strftime("%H-%M-%S")
 	os.system("sudo fswebcam --fps 15 -S 20 -s brightness=80% -r 512x384 -q var/www/html/photos/"+waktu+".jpg")
 	return 


def send_image():
	"""
	"""
	pass

@app.route("/logging")
def logging():
	import request
	"""
		This method will do the logging
	"""
	# TODO IMPLEMENT LOGGING INTO THE SERVER LOGGING

	# Destroy session for next use!
	for key in session.keys():
		session.pop[key]

	return redirect_url(url_for('index'))


@app.route("/get_camera_data")
def get_camera_data():
	"""
		This method will captured the traveller photo and store it into logging folder
	"""	
	take_image()
	send_image()
	if session['verifikasi_fingerprint'] and session['status_cekal']:
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
	app.secret_key = 'nyemnyemnyem'
	app.run(host=app.config['HOST'], port=int(app.config['PORT']))