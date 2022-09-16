#!/bin/bash

# Add this script to a scheduling system to run every x hours or so
echo "Attempting relogin at $(date)"

# Skip relogin if recently logged in
LAST_LOGIN=$(< /home/gandharv/Scripts/lastLogin.txt)
TIME_SINCE_LOGIN=$(expr $(date +%s) - $LAST_LOGIN)
LOGIN_COOLDOWN=$(expr 8 '*' 60 '*' 60)
if ((TIME_SINCE_LOGIN < LOGIN_COOLDOWN)); then
	echo "Already logged in recently"
	exit 1
fi

# Checking if connected to IIT (BHU)
curl  --silent --connect-timeout 5 -I http://192.168.249.1:1000/login?
if [ $? -ne 52 ]; then
	echo "Not connected to the wifi IIT(BHU)!"
	exit $retVal
fi

# Setting up params
PASS=$(cat /home/gandharv/Scripts/iitbhu_wifi_pass.txt)
ROLL='20124018'
LOGIN_LINK='http://192.168.249.1:1000/login?'

# Making the warning dialog "Always on top"
sleep 1 && wmctrl -F -a "Relogin Warning!" -b add,above &

# Asking user before relogin
zenity --question --window-icon="warning" --title="Relogin Warning!" --text="Relogin to wifi in 30s. Continue?" --timeout=30
userChoice=$?
if [ $userChoice -eq 1 ]; then
	echo "Skipped relogin"
	exit $userChoice
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
	echo "$(date +%s)" > /home/gandharv/Scripts/lastLogin.txt
else
	echo "Error logging in!"
	exit $retVal
fi