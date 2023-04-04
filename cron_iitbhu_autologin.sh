#!/bin/bash

last_login_file='/home/gandharv/Scripts/secrets/lastLogin.txt'
wifi_pass_file='/home/gandharv/Scripts/secrets/iitbhu_wifi_pass.txt'

# Add this script to a scheduling system to run every x hours or so
echo "Attempting relogin at $(date +'%A %d %B %Y %T %Z')"
# Skip relogin if recently logged in
LAST_LOGIN=$(cat last_login_file)
TIME_SINCE_LOGIN=$(expr $(date +%s) - $LAST_LOGIN)
LOGIN_COOLDOWN=$(expr 4 '*' 60 '*' 60 - 5 '*' 60)
if ((TIME_SINCE_LOGIN < LOGIN_COOLDOWN)); then
	echo "Already logged in recently"
	if test "$1" = "-f"; then
		echo "Ignoring last login.."
	else
		exit 1
	fi
fi

# Checking if connected to IIT (BHU)
curl  --silent --connect-timeout 5 -I http://192.168.249.1:1000/login?
if [ $? -ne 52 ]; then
	echo "Not connected to the wifi IIT(BHU)!"
	exit $retVal
fi

# Setting up params
PASS=$(cat wifi_pass_file)
ROLL='20124018'
LOGIN_LINK='http://192.168.249.1:1000/login?'

# Don't show relogin warning dialog if -f option is present
if test "$1" != "-f"; then
	# Making the warning dialog "Always on top"
	sleep 1 && wmctrl -F -a "Relogin Warning!" -b add,above &

	# Asking user before relogin
	zenity --question --window-icon="warning" --title="Relogin Warning!" --text="Relogin to wifi in 30s. Continue?" --timeout=30
	userChoice=$?
	if [ $userChoice -eq 1 ]; then
		echo "Skipped relogin"
		exit $userChoice
	fi
fi

echo "Logging out.."
LOGOUT_OUTPUT=$(curl --silent --connect-timeout 5 http://192.168.249.1:1000/logout?)

MAGIC=$(curl --connect-timeout 5 --silent \
	-X GET http://192.168.249.1:1000/login? 2>&1 | grep -E "magic" | awk -F'"' '{print $6}')

echo "Logging in.."
CURL_OUTPUT=$(curl --connect-timeout 5 --silent \
	-d "4Tredir=${LOGIN_LINK}&magic=${MAGIC}&=&username=${ROLL}&password=${PASS}" \
	-X POST http://192.168.249.1:1000 2>&1)

retVal=$?
if [ $retVal -eq 0 ]; then
	echo "Logged in!"
	echo "$(date +%s)" > last_login_file
else
	echo "Error logging in!"
	exit $retVal
fi
