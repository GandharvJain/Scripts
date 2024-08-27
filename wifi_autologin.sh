#!/bin/sh
IFACE=$1
ACTION=$2

echo $IFACE, $ACTION >> /home/gandharv/networklogs

[ "$ACTION" = "up" ] || exit 0
[ "$IFACE" != "lo" ] || exit 0

sleep 10
echo -n "[if-up.d] ($IFACE) " >> /home/gandharv/Scripts/secrets/autologin.log
DISPLAY=:1 /bin/bash /home/gandharv/Scripts/cron_iitbhu_autologin.sh -f >> /home/gandharv/Scripts/secrets/autologin.log
