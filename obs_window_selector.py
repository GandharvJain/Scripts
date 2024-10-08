#!/home/gandharv/python-user/bin/python3

import os

# This script changes window in window capture source to 
# the currently focused window or the one chosen by select tool

secrets_path = '/home/gandharv/Scripts/secrets/'
pass_file = secrets_path + "obs_password.txt"

# Requirements: OBS, obs-cli from snap store, xdotool and pgrep

def select():
	getWindow = "xdotool getactivewindow"
	# Uncomment to select window manually instead of choosing the focused window
	# getWindow = "xdotool selectwindow"
	windowId = os.popen(getWindow).read().strip()
	password = ""

	# Read password from file. First line should be password.
	# Comment these two lines if you want to store your password above.
	with open(pass_file, 'r') as f:
		password = f.readline().strip()

	source = "Temp"
	scene = "Switch"

	cmd = ""
	cmd += '''obs-cli -p %s ''' % password
	cmd += '''SetSourceSettings='{"sourceName": "%s", ''' % source
	cmd += '''"sourceSettings": {"capture_window": "%s"} }' ''' % windowId
	cmd += '''SetCurrentScene=\'{"scene-name": "%s"}' ''' % scene
	# print(cmd)

	log = os.popen(cmd).read().strip()
	# print(log)

obs_pid = os.popen("pgrep -x obs").read().strip()
if obs_pid:
	select()
else:			# Define another function for
	pass		# shortcut if obs isn't open