#!/bin/bash

# Checking if connected to IIT (BHU)
curl --connect-timeout 5 -I http://192.168.249.1:1000/login?
if [ $? -eq 28 ]; then
	echo "Not connected to the wifi IIT(BHU)!"
	exit $retVal
fi

# Setting up params
PASS=$(cat /home/gandharv/Scripts/iitbhu_wifi_pass.txt)
ROLL='20124018'
LOGIN_LINK='http://192.168.249.1:1000/login?'

while true; do
	echo "Logging out..."
	curl http://192.168.249.1:1000/logout?
	
	MAGIC=$(curl --silent -X GET http://192.168.249.1:1000/login? 2>&1 | grep -E "magic" | awk -F'"' '{print $6}')

	echo "Logging in..."
	CURL_OUTPUT=$(curl --silent -d "4Tredir=${LOGIN_LINK}&magic=${MAGIC}&=&username=${ROLL}&password=${PASS}" -X POST http://192.168.249.1:1000 2>&1)
	retVal=$?
	if [ retVal -eq 0 ]; then
		echo "Logged in at $(date)!"
	else
		echo "Error logging in!"
		exit retVal
	fi

	echo "Sleeping..."
	sleep 7200
done

# Below lines are not needed as the link http://192.168.249.1:1000/logout? logs you out
# LOGOUT_LINK=$(echo -n $CURL_OUTPUT | awk -F'"' '{print $2}' | sed "s/keepalive/logout/")
# echo $LOGOUT_LINK > /home/gandharv/Scripts/iitbhu_wifi_logout_link.txt
