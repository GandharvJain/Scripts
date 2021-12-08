#!/usr/bin/python

import subprocess
import os

# nvidia prime profiles: "nvidia", "intel" and "on-demand"
prime_profile = os.popen('prime-select query').read().strip()
obs_profile = "Nvidia"
scene = "Chrome"

if prime_profile == "intel":
	obs_profile = "Intel"

obs_pid = os.popen("pgrep obs").read().strip()

def start():
	command = "snap run obs-studio --profile " + obs_profile + " --scene " + scene + " --startrecording --minimize-to-tray"
	p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

	output, err = p.communicate()
	output = output.decode()
	p_status = p.wait()

	f = open("/home/gandharv/obs_log.txt", "w+")
	f.write(output + "\nReturn Code: " + str(p_status))

def end():
	stop_recording_hotkey = "ctrl+alt+R"
	os.popen("xdotool key " + stop_recording_hotkey)
	os.popen("sleep 1 && kill -9 " + obs_pid.split()[0])


# print(obs_pid)
if not obs_pid:
	start()
else:
	end()