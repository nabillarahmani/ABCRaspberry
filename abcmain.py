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


	def get_hex_string(array_of_hex):
		"""
		"""
		hex_field_map_string = ""
		for x in array_of_hex:
			hex_field_map_string += (str)hex(x)
		return hex_field_map_string


	def parse_field_map(field_map):
		"""
		@input : array of data 
		@return: string of binary
		"""
		hex_field_map_string = get_hex_string(field_map)

		h_size = len(hex_field_map_string) * 4
		string_binary_field = (bin(int(hex_field_map_string, 16))[2:] ).zfill(h_size)
		return string_binary_field


	def substring_hex(string, start, length):
		"""
		"""
		return string[start*2:length*2]
	

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

			# GET CARD TYPE (XIRCA / DAM)
			card_id = "0x" + get_hex_string(data)
			card_id_int = int(card_id, 0)

			# SELECT EF (FIELD MAP + LENGTH MAP)
			APDU_FIELD = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x00]
			data, sw1, sw2 = connection.transmit(APDU_FIELD)

			#Get field map + length map
			APDU_GET_FIELD = [0x00, 0xB0, 0x00, 0x00, 0x33]
			data, sw1, sw2 = connection.transmit(APDU_GET_FIELD)

			# Parse Field Map to check whether it is empty or not
			# Field map = 10101010100011 (in binary)
			field_map = parse_field_map(data)
			flag_empty = False

			# Check for each element whether it is filled yet or not
			for element in data:
				converted_dec = hex(element)
				# IF there is one single element which not FF, then it is filled
				if converted_dec != '0xFF':
					flag_empty = True


			if flag_empty == True:
				#sdcard disconnect
				return render_template('failed_readcard.html')

			# Get the total length of map
			total_length_map = 0
			for x in data:
				total_length_map += x

			# SELECT EF FOR FIRST DATA
			APDU_SELECT_DATA_1 = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x01, 0x01]
			data, sw1, sw2 = connection.transmit(APDU_SELECT_DATA_1)			

			

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