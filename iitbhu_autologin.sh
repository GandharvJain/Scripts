#!/bin/bash

curl --connect-timeout 5 -I http://192.168.249.1:1000/login?
retVal=$?
if [ $retVal -eq 28 ]; then
	echo "Not connected to the wifi IIT(BHU)!"
	exit $retVal
fi

PASS=$(cat /home/gandharv/Scripts/iitbhu_wifi_pass.txt)
ROLL='20124018'
LOGIN_LINK='http://192.168.249.1:1000/login?'
MAGIC=$(curl --silent -X GET http://192.168.249.1:1000/login? 2>&1 | grep -E "magic" | awk -F'"' '{print $6}')

LOGOUT_LINK=$(curl --silent -d "4Tredir=${LOGIN_LINK}&magic=${MAGIC}&=&username=${ROLL}&password=${PASS}" -X POST http://192.168.249.1:1000 2>&1)
LOGOUT_LINK=$(echo -n $LOGOUT_LINK | awk -F'"' '{print $2}' | sed "s/keepalive/logout/")

echo $LOGOUT_LINK > /home/gandharv/Scripts/iitbhu_wifi_logout_link.txt
