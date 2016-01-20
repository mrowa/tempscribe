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
GPIO.setup(20, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(21, GPIO.IN, pull_up_down = GPIO.PUD_UP)

def printFunc(channel):
	print 'button pressed', channel

GPIO.add_event_detect(20, GPIO.FALLING, callback=printFunc, bouncetime=300)
GPIO.add_event_detect(21, GPIO.FALLING, callback=printFunc, bouncetime=300)

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
		cursor.commit()
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

		# pins... just debug
		# print 'input 20', GPIO.input(20), '21', GPIO.input(21)

		# save to sqlite
		cursor.execute(
		"INSERT INTO reads (sensor_id, timestamp, value)  VALUES (?,julianday('now'),?)",
		(id, temp))
	
		connection.commit()

	
	temp = temps[defaultslave]
	list.append(temp)

	if counter < chartwidth - 1:
		counter += 1

	# Clear image buffer.
	draw.rectangle((0,0,83,47), outline=255, fill=255)
	# Enumerate characters and draw them offset vertically based on a sine wave.

	mintemp = min(list)
	maxtemp = max(list)
	minshown = mintemp - tolerance
	maxshown = maxtemp + tolerance
	difftemp = maxtemp - mintemp 
	diffshown = maxshown - minshown

	print datetime.now(), 'temp', list[0], 'min', mintemp, 'max', maxtemp

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
