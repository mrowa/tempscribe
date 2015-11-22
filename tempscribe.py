# encoding=utf8

#
# :)
#

import math
import time
import re
import collections

import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

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
font = ImageFont.load_default()

# Alternatively load a TTF font.
# Some nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('/home/pi/mrowa/Symbola.ttf', 8)

# Create drawing object.
draw = ImageDraw.Draw(image)

# Define text and get total width.
text = 'Love my sweet Kitty Kacha <3 :3'
maxwidth, height = draw.textsize(text, font=font)

# Set starting position.
startpos = 83
pos = startpos

# ion is 84x48 pixels, so the screen can learn 84 temperatures
height = 48
width = 84
chartwidth = 10
list = collections.deque(maxlen=width)
# counter is to keep the length of deque (which is not present)
counter = 0

# how much space to leave for (in degrees celsius)
tolerance = 0.5

# Animate text moving in sine wave.
print 'Press Ctrl-C to quit.'
while True:

	# read temperature from 1-wire devices (right now we use constant file
	# , later on we need more wires)
	f = open('/sys/bus/w1/devices/28-031571fb73ff/w1_slave', 'r')
	str = f.read()

	strval = re.findall(r'\d+', str)[-1]
	val = float(strval)
	temp = val / 1000

	list.append(temp)

	if counter < width - 1:
		counter += 1

	# Clear image buffer.
	draw.rectangle((0,0,83,47), outline=255, fill=255)
	# Enumerate characters and draw them offset vertically based on a sine wave.

	mintemp = min(list) -0.5
	maxtemp = max(list) +0.5
	difftemp = maxtemp - mintemp 

#	print mintemp, maxtemp, difftemp

	for index, temp in enumerate(list):
		y = height - (temp - mintemp) / difftemp * height
		x = width -1 - counter + index
		# counter checks how many elements are in list,
		#draw.point([index, y])
		draw.line(((x, y), (x, height)))
		if index == 0:
			print 'temp', temp, 'y', y, 'min', mintemp, 'max', maxtemp


	# Draw the image buffer.
	disp.image(image)
	disp.display()
	# Move position for next frame.
#	pos -= 2
	# Start over if text has scrolled completely off left side of screen.
#	if pos < -maxwidth:
#		pos = startpos
	# Pause briefly before drawing next frame.
#	time.sleep(1.0)
