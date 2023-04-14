#!/bin/bash

okular_config="/home/gandharv/.okular_open_files"

xargs -0 -d '\n' -a $okular_config flatpak run org.kde.okular &
sleep 3

okular_pid=`pgrep -n okular-bin`
while [[ $okular_pid == `pgrep okular-bin` ]]; do
	open_files="`lsof -p $okular_pid | grep -o /home.*pdf | sort`"
	[[ -n $open_files ]] && echo "$open_files" > $okular_config
	sleep 300
done