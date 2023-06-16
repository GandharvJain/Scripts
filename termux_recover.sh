#!/bin/bash

# Ask for "Draw over apps" permission
echo "Enable \"Display over other apps\" in the settings"
am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d "package:com.termux"
# Alternate version in case the setting is not located in the app info page
# am start --user 0 -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:com.termux"

yes | pkg update && yes | pkg upgrade
pkg install tar jq wget gnupg termux-api -y
yes Y | termux-setup-storage
sleep 5

# Ask for install app permission
echo "Allow Termux permission to install apps"
am start -a android.settings.MANAGE_UNKNOWN_APP_SOURCES
sleep 10

deployFdroidApp() {
	package_name=$1
	force_install=$2
	# Getting latest version number of app
	app_version=$(wget -qO - https://f-droid.org/api/v1/packages/$package_name | jq -r '.suggestedVersionCode')
	app_apk=$package_name"_"$app_version.apk
	# Getting official app name
	app_name=$(wget -qO - https://gitlab.com/fdroid/fdroiddata/-/raw/master/metadata/$package_name.yml | awk '/AutoName/ {print $1}')

	# Downloading apk
	wget "https://f-droid.org/repo/$app_apk"

	echo "Downloaded $app_apk"

	# Set allow-external-apps to true in ~/.termux/termux.properties
	value="true"; key="allow-external-apps"; file="/data/data/com.termux/files/home/.termux/termux.properties"; mkdir -p "$(dirname "$file")"; chmod 700 "$(dirname "$file")"; if ! grep -E '^'"$key"'=.*' $file &>/dev/null; then [[ -s "$file" && ! -z "$(tail -c 1 "$file")" ]] && newline=$'\n' || newline=""; echo "$newline$key=$value" >> "$file"; else sed -i'' -E 's/^'"$key"'=.*/'"$key=$value"'/' $file; fi

	# Installing apk
	if [[ ${force_install,,} =~ ^(y|yes)$ ]]; then
		termux-open --view $app_apk
	else
		termux-notification -t "Install $app_name" --action "termux-open --view $app_apk" &
	fi

	# Set allow-external-apps to false in ~/.termux/termux.properties
	value="false"; key="allow-external-apps"; file="/data/data/com.termux/files/home/.termux/termux.properties"; mkdir -p "$(dirname "$file")"; chmod 700 "$(dirname "$file")"; if ! grep -E '^'"$key"'=.*' $file &>/dev/null; then [[ -s "$file" && ! -z "$(tail -c 1 "$file")" ]] && newline=$'\n' || newline=""; echo "$newline$key=$value" >> "$file"; else sed -i'' -E 's/^'"$key"'=.*/'"$key=$value"'/' $file; fi
}

# Install Termux:API
deployFdroidApp com.termux.api yes

echo "Waiting for Termux:API to install"

is_error="dummy_text"
termux_api_available=false
while true; do
	# Testing if Termux:API is installed
	is_error=$(termux-api-start 2>&1 1>/dev/null)
	if [[ -z $is_error ]]; then
		termux_api_available=true
		break
	fi
	sleep 3
done

echo "Installed Termux:API"

choice=""
while [[ -z $choice ]]; do
	choice=$(termux-dialog confirm -t "Termux Recover Script" -i "Download extra apps?" | jq -r ".text")
	sleep 3
done

if [[ $choice = yes ]]; then
	# Update Termux
	deployFdroidApp com.termux no
	# Install Termux:Widget
	deployFdroidApp com.termux.widget no
	# Install Termux:Styling
	deployFdroidApp com.termux.styling no
fi

echo "Decrypting and extracting Termux backup..."

# Decrypting and extracting termux backup
if [[ termux_api_available = true ]]; then
	PASS=$(termux-dialog text -t 'Termux Backup Password' -p | jq -r '.text')
	gpg --batch --pinentry-mode loopback --passphrase $PASS -d /sdcard/termux-backup.tar.gz.gpg | tar zx -C /data/data/com.termux/files --recursive-unlink --preserve-permissions
else
	gpg -d /sdcard/termux-backup.tar.gz.gpg | tar zx -C /data/data/com.termux/files --recursive-unlink --preserve-permissions
fi

# Create termux shortcut
termux-notification -t "Install termux shortcuts" --action "am start -a android.intent.action.CREATE_SHORTCUT -n com.termux.widget/.TermuxCreateShortcutActivity"

echo "Finished Termux recovery"