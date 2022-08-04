#!/bin/bash

# Add this script to a scheduling system to run every x hours or so

# Checking if connected to IIT (BHU)
curl  --silent --connect-timeout 5 -I http://192.168.249.1:1000/login?
if [ $? -eq 28 ]; then
	echo "Not connected to the wifi IIT(BHU)!"
	exit $retVal
fi

# Setting up params
PASS=$(cat /home/gandharv/Scripts/iitbhu_wifi_pass.txt)
ROLL='20124018'
LOGIN_LINK='http://192.168.249.1:1000/login?'

echo "Attempting relogin at $(date)"

# Asking user before relogin
zenity --question --window-icon="warning" --title="Warning!" --text="Relogin to wifi in 30s. Continue?" --timeout=30
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
else
	echo "Error logging in!"
	exit retVal
fi