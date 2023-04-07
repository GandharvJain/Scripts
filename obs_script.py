#!/usr/bin/python3

import subprocess
import os

# Requirements: OBS, pgrep, kill and xdotool
# For rename dialog: zenity, wmctrl and notify-send

icon_path_0 = "/usr/share/icons/Yaru/256x256/actions/dialog-no.png"
icon_path_1 = "/usr/share/icons/Yaru/256x256/actions/dialog-yes.png"

# Set scene and profile name
obs_profile = "Nvidia"
scene = "Teams"
# Must be the same as the one in OBS
obs_save_path = "/home/gandharv/Videos"
# Name for log file
log_file = "obs_log.txt"


# nvidia prime profiles: "nvidia", "intel" and "on-demand"
prime_profile = os.popen('prime-select query').read().strip()
if prime_profile == "intel":
	obs_profile = "Intel"

# Get pid of OBS if already open
obs_pid = os.popen("pgrep -x obs -d' '").read().strip()

# Record Google Chrome if MS Teams is not open
MsTeams_pid = os.popen("pgrep -x teams -d' '").read().strip()
if not MsTeams_pid:
	scene = "Chrome"


def renameDialog():

	# Get list of files in recording folder
	file_list = []
	for (dirPath, dirNames, fileNames) in os.walk(obs_save_path):
		file_list.extend(os.path.join(dirPath, file) for file in fileNames if file != log_file)

	# Get last modified file, which should be the one OBS just created
	latest_file = max(file_list, key=os.path.getctime).replace(obs_save_path + '/', '')

	cmd = 'zenity --entry --width=400 --height=100 --title="Save as" --text="Enter recording name:\nPWD: %s/" --entry-text=' % obs_save_path
	cmd += latest_file

	while True:

		# Original path for file created by OBS
		src = os.path.join(obs_save_path, latest_file)

		# Making the rename dialog "Always on top"
		os.popen('sleep 1 && wmctrl -F -a "Save as" -b add,above &')
		
		# Showing the popup and getting the new name
		new_name = os.popen(cmd).read().strip()

		# Checking if clicked "Cancel"
		if new_name == "":

			# Making the warning dialog "Always on top"
			os.popen('sleep 1 && wmctrl -F -a "Important!" -b add,above &')
			
			# Show the warning
			ans = os.popen('zenity --question --window-icon="warning" --title="Important!" --text="Delete recording?"').close()

			if bool(ans) == False:
				# Deleting recording
				os.popen('gvfs-trash %s' % src)
				os.popen('notify-send -i %s "Deleted recording"' % icon_path_0)

				break

			continue

		# New path for recording
		dest = os.path.realpath(os.path.join(obs_save_path, new_name))

		try:
			# Rename recording
			os.renames(src, dest)

			head, tail = os.path.split(dest)
			os.popen('notify-send -i %s "Saved recording as %s" "at %s/"' % (icon_path_1, tail, head))

			break

		except Exception as e:
			os.popen('zenity --error --window-icon="error" --width=300 --text="%s" &' % str(e))


def startRecording():
	
	# Starts OBS, change if not installed from snap store
	command = "snap run obs-studio --profile " + obs_profile + " --scene " + scene + " --startrecording"
	p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

	# piping output of command to "output"
	# and waiting for OBS to end
	output, err = p.communicate()
	output = output.decode()
	p_status = p.wait()

	# Saving output and return code to log file
	f = open(os.path.join(obs_save_path, log_file), "w+")
	f.write(output + "\nReturn Code: " + str(p_status))


def endRecording():

	# Set the stop recording hotkey
	# Ensure hotkey behavior in OBS is set to "Never disable hotkeys"
	stop_recording_hotkey = "ctrl+alt+R"
	os.popen("xdotool key " + stop_recording_hotkey)

	# Specifies time to wait before OBS is closed
	# Increase sleep time if OBS takes long time to
	# processes the video at end. Default is 5 seconds.
	os.popen("sleep 5 && kill -9 " + obs_pid)

	# Comment this line if you don't want the rename dialog
	renameDialog()


# Check if OBS is already open
if not obs_pid:
	startRecording()
else:
	endRecording()