#!/usr/bin/python

import subprocess
import os

# nvidia prime profiles: "nvidia", "intel" and "on-demand"
prime_profile = os.popen('prime-select query').read().strip()

obs_profile = "Nvidia"
scene = "Chrome"
obs_save_path = "/home/gandharv/Videos"
log_file = "obs_log.txt"


if prime_profile == "intel":
	obs_profile = "Intel"

obs_pid = os.popen("pgrep -x obs").read().strip()


def renameDialog():

	file_list = []
	for (dirPath, dirNames, fileNames) in os.walk(obs_save_path):
		file_list.extend(os.path.join(dirPath, file) for file in fileNames if file != log_file)

	latest_file = max(file_list, key=os.path.getctime).replace(obs_save_path + '/', '')


	cmd = 'zenity --entry --width=400 --height=100 --title="Save as" --text="Enter recording name:\nPWD: %s/" --entry-text=' % obs_save_path
	cmd += latest_file

	while True:

		src = os.path.join(obs_save_path, latest_file)

		os.popen('sleep 1 && wmctrl -F -a "Save as" -b add,above &')
		new_name = os.popen(cmd).read().strip()

		if new_name == "":
			os.popen('sleep 1 && wmctrl -F -a "Important!" -b add,above &')
			ans = os.popen('zenity --question --window-icon="warning" --title="Important!" --text="Delete recording?"').close()
			if bool(ans) == False:
				os.remove(src)
				os.popen('notify-send -i /usr/share/icons/HighContrast/scalable/actions/dialog-cancel.svg "Deleted recording"')
				break
			continue

		dest = os.path.realpath(os.path.join(obs_save_path, new_name))

		try:
			os.renames(src, dest)

			head, tail = os.path.split(dest)
			os.popen('notify-send -i /usr/share/icons/HighContrast/scalable/actions/dialog-ok.svg "Saved recording as %s" "at %s/"' % (tail, head))

			break

		except Exception as e:
			os.popen('zenity --error --window-icon="error" --width=300 --text="%s" &' % str(e))


def start():
	command = "snap run obs-studio --profile " + obs_profile + " --scene " + scene + " --startrecording --minimize-to-tray"
	p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

	output, err = p.communicate()
	output = output.decode()
	p_status = p.wait()

	f = open(os.path.join(obs_save_path, log_file), "w+")
	f.write(output + "\nReturn Code: " + str(p_status))


def end():
	stop_recording_hotkey = "ctrl+alt+R"
	os.popen("xdotool key " + stop_recording_hotkey)
	os.popen("sleep 5 && kill -9 " + obs_pid.split()[0])
	renameDialog()


if not obs_pid:
	start()
else:
	end()