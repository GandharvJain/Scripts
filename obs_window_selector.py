#!/usr/bin/python

import os

def select():
	windowId = os.popen("xdotool getactivewindow").read().strip()
	with open("/home/gandharv/Scripts/password.txt", 'r') as f: 
		password = f.readline().strip()

	cmd = "obs-cli -p %s " % password
	cmd += 'SetSourceSettings=\'{"sourceName": "Temp", "sourceSettings": {"capture_window": "%s"} }\' ' % windowId
	cmd += 'SetCurrentScene=\'{"scene-name": "Switch"}\''

	log = os.popen(cmd).read().strip()


obs_pid = os.popen("pgrep -x obs").read().strip()
if obs_pid:
	select()
else:			# Define another function for
	pass		# shortcut if obs isn't open