#!/bin/bash

IS_PIPEWIRE=$(pactl info | grep PipeWire)

if [[ $IS_PIPEWIRE ]]; then
	echo Disabling pipewire...
	systemctl --user --now disable pipewire{,-pulse}.{socket,service}
	systemctl --user unmask pulseaudio
	systemctl --user --now enable pulseaudio.service pulseaudio.socket
else
	echo Enabling pipewire...
	systemctl --user --now disable pulseaudio.service pulseaudio.socket
	systemctl --user mask pulseaudio
	systemctl --user --now enable pipewire{,-pulse}.{socket,service}
fi