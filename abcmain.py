from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_dotenv import DotEnv
from flask_sqlalchemy import SQLAlchemy
from smartcard.System import readers
from __future__ import print_function
from smartcard.Exceptions import NoCardException
from smartcard.System import readers
from smartcard.util import toHexString


def create_app():
	env = DotEnv()
	app = Flask(__name__)
	env.init_app(app)
	env.eval(keys={
		'DEBUG': bool,
		'TESTING': bool
	})

	@app.route("/")
	def index():
		"""
			Render the view of index page.
		"""
		return render_template('index.html', title='', current_page='ABC Gate Home')


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
	

	def verification_document(extract_fingerprint, extract_picture):
		"""
			This will match between the data on smart card and on the given fingerprint
		"""
		return True	


	def verification_cekal(identification_number):
		"""
			This method will send a GET request into the API and retrieve cekal status
		"""
		return True


	def retrieve_image():
		"""
		"""
		pass


	def send_image():
		"""
		"""
		pass


	def logging():
		"""
		"""
		pass


	# Implementation of readcard using highlevel implementation
	@app.route("/readcard")
	def readcard():
		"""
			
		"""
		try:
			# get all the available readers
			r = readers()
			print("Available readers:", r)

			reader = r[0]
			print ("Using:", reader)

			connection = reader.createConnection()
			connection.connect()

			# SELECT MF
			SELECT = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]

			data, sw1, sw2 = connection.transmit(SELECT)
			print(data)
			print("Select Applet: %02X %02X" % (sw1, sw2))

			if sw1  == None and sw2 == None:
				# discard connection on card
				#
				return render_template('failed_detect_card.html')

			# Select DF
			APDU_DF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x10, 0x01]
			data, sw1, sw2 = connection.transmit(APDU_DF)

			# SELECT EF
			APDU_EF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0xFF]
			data, sw1, sw2 = connection.transmit(APDU_EF)

			# GET CARD TYPE
			APDU_CARD = [0x00, 0xB0, 0x00, 0x00, 0x02]
			data, sw1, sw2 = connection.transmit(APDU_CARD)			

			# GET CARD TYPE (XIRCA)
			card_id = data[1]


			# SELECT EF (FIELD MAP + LENGTH MAP)
			APDU_FIELD 		= [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x00]
			data, sw1, sw2 	= connection.transmit(APDU_FIELD)

			#Get field map + length map
			APDU_GET_FIELD 	= [0x00, 0xB0, 0x00, 0x00, 0x33]
			data, sw1, sw2 	= connection.transmit(APDU_GET_FIELD)
			flag_empty 		= True	

			# Check for each element whether it is filled yet or not
			for element in data:
				# IF there is one single element which not 255, then it is filled
				if element != 255:
					flag_empty = False

			if flag_empty == True:
				#sdcard disconnect
				return render_template('failed_readcard.html')
			# get the hex representation of respond
			# parse the first 3 bits from the respond to check the length
			# Field map = 10101010100011 (in binary) contains 3 bytes of binary representation
			respond_field_map 	= get_array_hex(data)
			field_map 			= parse_field_map(get_hex_string(respond_field_map, 0, 6))

			# Get the total length of map, after the first 3 bytes, it will define the length of each data
			total_length_map= 0
			length_map 		= data[3:]
			
			for length in length_map:

				total_length_map += length

			# SELECT EF FOR FIRST DATA 
			APDU_SELECT_DATA_1 = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x01]
			data, sw1, sw2 = connection.transmit(APDU_SELECT_DATA_1)			

			# handle if content inside card is null
			if sw1 == None and sw2 == None:
				#sdcard disconnect
				return render_template('failed_readcard.html')

			iteration 		= total_length_map / 240
			APDU_GET_DATA_1	= [0x00, 0xB0, 0x00, 0x00]
			respond_data_1	= []

			if total_length_map < 240:
				APDU_GET_DATA_1.append(total_length_map)
				respond, sw1, sw2 = connection.transmit(APDU_GET_DATA_1)	
			else:
				while iteration >= 0:
					if (total_length_map - 240) > 0 :
						# By default take 240 bytes from the card
						APDU_GET_DATA_1.append(240)
						data, sw1, sw2 = connection.transmit(APDU_GET_DATA_1)
						if sw1 == None and sw2 == None:
							#sdcard disconnect
							return render_template('failed_readcard.html')
						respond.extend(data)
						APDU_GET_DATA_1.pop()
						iteration -= 1
					else:
						# If smaller than the threshold then, take the remainder
						remainder = total_length_map - 240
						APDU_GET_DATA_1.append(remainder)
						data, sw1, sw2 = connection.transmit(APDU_GET_DATA_1)
						if sw1 == None and sw2 == None:
							#sdcard disconnect
							return render_template('failed_readcard.html')
						respond.extend(data)
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
				i += 1

			# Initialize the dictionnary
			respond_mapped = {'identification_number': '', 'full_name': '', 'icao_2' : '', 'photo' : ''}
			
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

				for data in data_photo:
					# do base64 encode to get the photo
					respond_mapped['photo'] += str(chr(data)

				print(respond_mapped['photo'])
			print(photo)

		except:
			return render_template('failed_readcard_content.html')

	@app.route("/readfingerprint")
	def readfingerprint():
		"""
		"""
		pass


	@app.route("/verification_process")
	def process_verification():
		"""
			This method will check the verification process between person to document
			This method will also check to server cekal
		"""
		pass


	@app.route("/get_camera_data")
	def get_camera_data():
		"""
		"""
		pass


	@app.route("/open_gate")
	def open_gate():
		"""
		"""
		pass


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

	return app


if __name__ == "__main__":
	application = create_app()
	application.run(host=application.config['HOST'], port=int(application.config['PORT']))