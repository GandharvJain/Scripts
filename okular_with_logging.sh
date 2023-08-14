#!/bin/bash

okular_config="/home/gandharv/.okular_open_files"

xargs -0 -d '\n' -a $okular_config flatpak run org.kde.okular &
sleep 3

okular_pid=`pgrep -n okular-bin`
process_dir="/proc/$okular_pid"
cmd_line_file="$process_dir/cmdline"
open_files_dir="$process_dir/fd"
cmd_line=`strings $cmd_line_file`

while [[ -d $process_dir ]]; do
	[[ `strings $cmd_line_file` != $cmd_line ]] && exit
	open_files="`ls -l1 $open_files_dir | sort | grep -o /home.*pdf`"
	[[ -n $open_files ]] && echo "$open_files" > $okular_config
	sleep 300
done
