#!/bin/bash
# this script runs tempscribe.py as sudo (for gpio memory access)

sudo echo "running at $(date)" > /home/pi/mrowa/running &

cd /home/pi/mrowa/tempscribe
 
sudo /home/pi/mrowa/tempscribe/run.sh > /home/pi/mrowa/log 2> /home/pi/mrowa/errors &
