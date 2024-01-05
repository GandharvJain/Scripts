#!/bin/bash

for card in $(pactl list cards short | grep bluez_card | cut -f 2); do
	if [ "$1" = "hsp" ]; then
		pacmd set-card-profile $card headset_head_unit
	else
		pacmd set-card-profile $card a2dp_sink
	fi
done