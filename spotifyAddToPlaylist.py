#!/usr/bin/python
import sys, os
# For 1920x1080 screen

def toStr(x, y):
	return str(x) + " " + str(y)

# Getting current and spotify window IDs
initialWinId = os.popen('xdotool getactivewindow').read().strip()
spotifyWinId = os.popen('xdotool search --onlyvisible --class Spotify').read().strip()

# Get coordinates of mouse pointer initially
x_init, y_init = [t[2:] for t in os.popen('xdotool getmouselocation').read().strip().split()][:2]

# Coordinates of Song name at the bottom left
x0 = 20
y0 = 1030

# Switching to Spotify and moving mouse to song name
os.popen("xdotool windowactivate --sync "+ spotifyWinId + " mousemove --sync " + toStr(x0, y0))

# Check for "Already added" popup by
# taking color of pixel at (950, 570) (might need experimenting to get coordinates right)
color = os.popen("xwd -id "+ spotifyWinId +" -silent | convert xwd:- -depth 8 -crop "+"1x1+950+570 txt:- | grep -om1 '#\w\+'").read().strip()
# print(color)

# Delay for closing the "Already added" popup
# Different color for if the mouse hovers over the "Don't add" button
if color in ["#1ED760", "#1DB954", "#00CB4E", "#02CA4F", "#1ACF5F", "#00EB59"]:
	os.popen("xdotool click --repeat 2 --delay 200 1")

# Rank of the playlist in the "add to playlist" dialog box
# Rank 0 for the "Add to new playlist" button
rank = 1

# Right click on song name then left click on "Add to playlist" button
# then left click on playlist name and restore original window and mouse location
command = "xdotool click 3 mousemove --sync " + toStr(x0+95, y0-70) + " click 1"+\
" mousemove --sync " + toStr(x0+280, y0-30*rank) + " click 1"+\
" windowactivate " + initialWinId + " mousemove " + toStr(x_init, y_init)

os.popen(command)