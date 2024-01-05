#!/bin/bash

if [ "$1" = "hsp" ]; then
	pacmd set-card-profile $(pactl list cards short | grep bluez_card | cut -f 2) headset_head_unit
else
	pacmd set-card-profile $(pactl list cards short | grep bluez_card | cut -f 2) a2dp_sink
fi