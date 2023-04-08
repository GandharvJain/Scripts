#!/bin/bash

okular_config="/home/gandharv/.okular_open_files"

while [[ -z `pgrep okular-bin` ]]; do
	xargs -0 -d '\n' -a $okular_config flatpak run org.kde.okular &
	sleep 3
done

okular_pid=`pgrep okular-bin`
while [[ $okular_pid == `pgrep okular-bin` ]]; do
	open_files="`lsof -p $okular_pid | grep -o /home.*pdf | sort`"
	[[ -n $open_files ]] && echo "$open_files" > $okular_config
	sleep 900
done