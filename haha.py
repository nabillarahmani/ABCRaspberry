import os

url = 'data/'
data = ''
if os.path.isfile(url +'information_taken.txt'):
	f = open(url +'information_taken.txt')
	data = f.read()
	f.close

print(data)
print(data.split("\n"))
smartcard_extract = {}
for data in data.split("\n"):
	smartcard_extract[data.split(': ')[0]] = data.split(': ')[1]
print(smartcard_extract)