#!/bin/bash

check_str=$(pactl info | grep -i pipewire)


for card in $(pactl list cards short | grep bluez_card | cut -f 2); do
	if [[ -z $check_str ]]; then
		if [ "$1" = "hsp" ]; then
			pacmd set-card-profile $card headset_head_unit
		else
			pacmd set-card-profile $card a2dp_sink
		fi
	else
		if [ "$1" = "hsp" ]; then
			pactl set-card-profile $card headset-head-unit
		else
			pactl set-card-profile $card a2dp-sink
		fi
	fi
done