#!/usr/bin/python
import sys, os
import math as m
# For 1920x1080 screen

def toStr(x, y):
	return str(x) + " " + str(y)

def hex2rgb(value):
	r = int(value[1:3], 16)
	g = int(value[3:5], 16)
	b = int(value[5:7], 16)
	return (r, g, b)

def dist(rgb1, rgb2):
	tmp = tuple(map(lambda i, j: (i-j)**2, rgb1, rgb2))
	return m.sqrt(sum(list(tmp)))

# Getting current and spotify window IDs
initialWinId = os.popen('xdotool getactivewindow').read().strip()
spotifyWinId = os.popen('xdotool search --onlyvisible --class Spotify').read().strip()

if spotifyWinId == "":
	sys.exit()
# Get coordinates of mouse pointer initially
x_init, y_init = [t[2:] for t in os.popen('xdotool getmouselocation').read().strip().split()][:2]

# Coordinates of Song name at the bottom left
x0 = 20
y0 = 1030

# Switching to Spotify and moving mouse to song name
os.popen("xdotool windowactivate --sync "+ spotifyWinId + " mousemove --sync " + toStr(x0, y0) + " sleep 0.1")

# Check for "Already added" popup by
# taking color of pixel at (950, 570) (might need experimenting to get coordinates right)
color = os.popen("xwd -id "+ spotifyWinId +" -silent | convert xwd:- -depth 8 -crop "+"1x1+950+570 txt:- | grep -om1 '#\w\+'").read().strip()
# print(color)

# Delay for closing the "Already added" popup
# Range of green color for the "Don't add" button
if dist(hex2rgb(color), hex2rgb("#1acf5f")) < 90:
	os.popen("xdotool click 1 sleep 0.3")

# Rank of the playlist in the "add to playlist" dialog box
# Rank 0 for the "Add to new playlist" button
rank = 1

# Right click on song name then left click on "Add to playlist" button
# then left click on playlist name and restore original window and mouse location
command = "xdotool click 3 mousemove --sync " + toStr(x0+95, y0-70) + " click 1"+\
" mousemove --sync " + toStr(x0+280, y0-30*rank) + " click 1"+\
" windowactivate " + initialWinId + " mousemove " + toStr(x_init, y_init)

os.popen(command)