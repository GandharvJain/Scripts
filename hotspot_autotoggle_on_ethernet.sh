#!/bin/sh
IFACE=$1
ACTION=$2

# Exit if a non-ethernet interface is turned on
case $IFACE in
	et*) ;; #For classic kernel-native ethX naming
	en*) ;; #For udev based en* naming
	*) exit 0 ;; #For non-ethernet/LAN connections, exit
esac

case $ACTION in
	up) # Turn wifi on, then turn hotspot on after 3 seconds
	/bin/nmcli radio wifi on && /bin/sleep 3 && /bin/nmcli connection up Hotspot
	;;
	down) # Turn Hotspot off
	/bin/nmcli connection down Hotspot
	;;
esac
