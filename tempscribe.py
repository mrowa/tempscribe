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

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

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

# thermometer device file
tempfile = open('/sys/bus/w1/devices/28-031571fb73ff/w1_slave', 'r')

print 'Press Ctrl-C to quit.'
while True:
	# read w1 thermometer data file
	tempfile.seek(0)
	strf = tempfile.read()

	strval = re.findall(r'\d+', strf)[-1]
	val = float(strval)
	temp = val / 1000

	# save to sqlite
	cursor.execute(
	"INSERT INTO reads (sensor_id, timestamp, value)  VALUES (?,julianday('now'),?)",
	(1, temp))
	
	connection.commit()

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

