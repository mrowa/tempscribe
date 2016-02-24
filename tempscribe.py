# encoding=utf8

#
# :)
#

import math
import time
import re
import collections
import sqlite3
from datetime import datetime

import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI

import RPi.GPIO as GPIO

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

# here - we add elements to work with the GPIO
# BCM means pin numbers not as on board, but as on CPU pinouts.
GPIO.setmode(GPIO.BCM) 
GPIO.setup(14, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
GPIO.setup(15, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
GPIO.setup(18, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

def printChart(elements):
	print 'printChart', getMode(), 'count', len(elements)
	draw.rectangle((0,0,83,47), outline=255, fill=255)

	if not len(elements):
		elements = [1,1]

	minElem = min(elements)
	maxElem = max(elements)
	minShown = minElem - tolerance
	maxShown = maxElem + tolerance
	diffTemp = maxElem - minElem
	diffShown = maxShown - minShown
	count = len(elements)

	#print minElem, maxElem, minShown, maxShown, diffTemp, diffShown, count

	for index, val in enumerate(elements):
		y = height - (val - minShown) / diffShown * height
		x = width - count + index - 1
		draw.line(((x, y), (x, height)))

	currTimes = -(times[0] -1)
	timestr = str(currTimes)
	if currTimes > 0:
		timestr = '+' + timestr		

	draw.text((0,0), str(round(maxElem,1)), font=font, fill=0)
	draw.text((0,37), str(round(minElem,1)), font=font, fill=0)
	draw.text((0,12), str(timestr), font=font, fill=0)
	draw.text((1,22), getMode(), font=font, fill=0)

	disp.image(image)
	disp.display()
	

def printFunc(channel):
	print 'button pressed', channel

def changeModeClicked(channel):
	if channel == 14:
		print 'channel 14 run'
		changeMode()

# this is current mode of operation: M, Q, H, D, W (minute, quarter, hour, day, week)
mode = ['M'];

def getMode():
	return mode[0]

def isMode(testedMode):
	return mode[0] == testedMode

def setMode(newMode):
	mode[0] = newMode

modes = {
	'Q': '(24*4)',
	'H': '24',
	'D': '1',
	'W': '(1.0/7)'
}

historySQL = """SELECT AVG(value) FROM reads
WHERE
timestamp >= julianday('now') - (1.0 / ?) * ?
AND timestamp < julianday('now') - (1.0 / ?) * (? - 1)
AND sensor_id = 1
GROUP BY CAST(timestamp * ? * ?  as int), sensor_id
ORDER BY timestamp DESC;"""

times = [1]

def readData():
	mode = getMode()
	modeTime = modes[mode]
	newConn = sqlite3.connect('tempscribe.data')
	curs = newConn.cursor()
	curs.execute(historySQL, (modeTime, times[0], modeTime, times[0], modeTime, 64))
	found = curs.fetchall()
	newConn.close()
	return [(i[0]) for i in found]

def changeMode():
	times[0] = 1
	oldMode = getMode()
	if isMode('M'):
		setMode('Q')
	elif isMode('Q'):
		setMode('H')
	elif isMode('H'):
		setMode('D')
	elif isMode('D'):
		setMode('W')
	else:
		setMode('M')
	print 'mode changed from', oldMode, 'to', getMode()
	reprintCharts()

def reprintCharts():
	if not isMode('M'):
		oldMode = getMode()
		oldTime = times[0]
		elements = readData()
		print 'oldmode is current mode'
		while isMode(oldMode) and oldTime == times[0]:
			printChart(elements)
			time.sleep(1.0)
		print 'oldmode is not current mode'

def future(channel):
	print 'moved to future'
	times[0] = times[0] - 1
	reprintCharts()

def past(channel):
	print 'moved to past'
	times[0] = times[0] + 1
	reprintCharts()

GPIO.add_event_detect(14, GPIO.FALLING, callback=changeModeClicked, bouncetime=300)
GPIO.add_event_detect(15, GPIO.FALLING, callback=future, bouncetime=300)
GPIO.add_event_detect(18, GPIO.FALLING, callback=past, bouncetime=300)


restartDatabase = False

# create sqlite table if not exists
sqlcreatestring = """PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

DROP TABLE IF EXISTS reads;
DROP TABLE IF EXISTS sensor;

CREATE TABLE IF NOT EXISTS sensor 
(
	id integer primary key not null,
	address text not null, 
	name text not null
);
CREATE TABLE IF NOT EXISTS reads 
(
	sensor_id integer not null,
	timestamp real not null,
	value real not null,
	FOREIGN KEY (sensor_id) REFERENCES sensor(id)
);

INSERT INTO sensor VALUES (1, '28-031571fb73ff', 'luźny');

COMMIT;"""

connection = sqlite3.connect('tempscribe.data')

if restartDatabase:
	print 'rebuilding database'
	connection.executescript(sqlcreatestring)
	print 'database rebuilded'
else:
	print 'not rebuilding database'

cursor = connection.cursor()

# Raspberry Pi hardware SPI config:
DC = 23
RST = 24
SPI_PORT = 0
SPI_DEVICE = 0

# Hardware SPI usage:
disp = LCD.PCD8544(DC, RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=4000000))

# Initialize library.
disp.begin(contrast=50)

# Clear display.
disp.clear()
disp.display()

# Create image buffer.
# Make sure to create image with mode '1' for 1-bit color.
image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))

# Load default font.
font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 10)

# Alternatively load a TTF font.
# Some nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('/home/pi/mrowa/Symbola.ttf', 8)

# Create drawing object.
draw = ImageDraw.Draw(image)

# Set starting position.
startpos = 83
pos = startpos

# ion is 84x48 pixels, so the screen can learn 84 temperatures
height = 48
width = 84
chartwidth = 84-20
list = collections.deque(maxlen=chartwidth)
# counter is to keep the length of deque (which is not present)
counter = -1

# how much space to leave for (in degrees celsius)
tolerance = 0.5

# main slave to read temp from
defaultslave = '28-031571fb73ff'

# open w1 bus master and read slaves
masterfile = open('/sys/bus/w1/drivers/w1_master_driver/w1_bus_master1/w1_master_slaves', 'r')
mastercontent = masterfile.read()
slaves = mastercontent.split()

thermfilenames = map(lambda slave: '/sys/bus/w1/devices/'+slave+'/w1_slave', slaves)
thermfiles = map(lambda filename: open(filename, 'r'), thermfilenames)

slaveids = {}
slavefiles = {}

for slave in slaves:
	cursor.execute('SELECT id FROM sensor WHERE address LIKE ? LIMIT 1', (slave,))
	id = cursor.fetchone()
	if id is None:
		cursor.execute('INSERT INTO sensor (address, name) VALUES (?, ?)', (slave, 'autoadded'))
		connection.commit()
		cursor.execute('SELECT id FROM sensor WHERE address LIKE ? LIMIT 1', (slave,))
		id = cursor.fetchone()
	slaveids[slave] = int(id[0])
	filename = '/sys/bus/w1/devices/'+slave+'/w1_slave'
	slavefile = open(filename, 'r')
	slavefiles[slave] = slavefile

# thermometer device file
tempfile = open('/sys/bus/w1/devices/28-031571fb73ff/w1_slave', 'r')

temps = {}

print 'Press Ctrl-C to quit.'
while True:
	# read w1 thermometer data file
	for slave in slaves:
		thermfile = slavefiles[slave]
		id = slaveids[slave]
		thermfile.seek(0)
		strf = thermfile.read()

		strval = re.findall(r'\d+', strf)[-1]
		val = float(strval)
		temp = val / 1000
		temps[slave] = temp

		valid = re.search(r'YES', strf) is not None
		if not valid:
			print 'invalid read', temp, strf.replace('\n', '; ')

		if valid and (temp > 84.9 or temp < 0.1):
			valid = False
			print 'valid read, but suspicious, omitting', temp

		# pins... just debug
		# print 'input 20', GPIO.input(20), '21', GPIO.input(21)

		if valid:
		# save to sqlite
			cursor.execute(
			"INSERT INTO reads (sensor_id, timestamp, value)  VALUES (?,julianday('now'),?)",
			(id, temp))

			try:	
				connection.commit()
			except sqlite3.OperationalError:
				print 'oopsie daisy, we cant commit'

	
	temp = temps[defaultslave]
	list.append(temp)

	if counter < chartwidth - 1:
		counter += 1

	mintemp = min(list)
	maxtemp = max(list)
	minshown = mintemp - tolerance
	maxshown = maxtemp + tolerance
	difftemp = maxtemp - mintemp 
	diffshown = maxshown - minshown

	print datetime.now(), 'temp', list[0], 'min', mintemp, 'max', maxtemp

	if isMode('M'):

		# Clear image buffer.
		draw.rectangle((0,0,83,47), outline=255, fill=255)


		# draw the chart
		for index, temp in enumerate(list):
			y = height - (temp - minshown) / diffshown * height
			x = width - counter + index -1
			# counter checks how many elements are in list,
			#draw.point([x, y])
			draw.line(((x, y), (x, height)))

		draw.text((0,0), str(round(maxtemp,1)), font=font, fill=0)
		draw.text((0,37), str(round(mintemp,1)), font=font, fill=0)
		draw.text((0,12), str(round(temp,1)), font=font, fill=0)
		draw.text((1,22), 'M', font=font, fill=0)

		# Draw the image buffer.
		disp.image(image)
		disp.display()

GPIO.cleanup()
