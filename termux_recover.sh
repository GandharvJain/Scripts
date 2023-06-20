#!/bin/bash

# To store history in .bash_history after script ends
export HISTTIMEFORMAT="[%F %T] "
export HISTFILE=~/.bash_history
set -o history

BACKUP_FILE="/sdcard/termux-backup.tar.gz.gpg"
TERMUX_FILES="/data/data/com.termux/files"
TERMUX_RECOVERY="$TERMUX_FILES/termux_recovery"
SCRIPT_PATH=$(realpath "$0")

# Creating $TERMUX_RECOVERY directory and moving script to it to prevent deleting it when extracting $BACKUP_FILE
if [[ "$SCRIPT_PATH" != "$TERMUX_RECOVERY/termux_recover.sh" ]]; then
	mkdir "$TERMUX_RECOVERY"
	cp "$SCRIPT_PATH" "$TERMUX_RECOVERY/termux_recover.sh"
	exec "$TERMUX_RECOVERY/termux_recover.sh"
	return 0
fi
cd "$TERMUX_RECOVERY"

# Ask for "Draw over apps" permission
echo "[termux_recover.sh] Enable \"Display over other apps\" in the settings"
am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d "package:com.termux"
# Alternate version in case the setting is not located in the app info page
# am start --user 0 -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:com.termux"

# Installing necessary packages
while true; do
	yes | pkg update
	pkg install tar jq gnupg termux-api -y && installed=true || installed=false
	$installed && break || termux-change-repo
done

# Enable access to internal storage
yes Y | termux-setup-storage
sleep 5

# Ask for install app permission
echo "[termux_recover.sh] Allow Termux permission to install apps"
am start -a android.settings.MANAGE_UNKNOWN_APP_SOURCES

# Finding best mirror
echo "[termux_recover.sh] Finding best server"
MIRRORS=(
	'https://f-droid.org/repo/'
	'https://mirror.cyberbits.eu/fdroid/repo/'
	'https://fdroid.tetaneutral.net/fdroid/repo/'
	'https://ftp.fau.de/fdroid/repo/'
	'https://plug-mirror.rcac.purdue.edu/fdroid/repo/'
	'https://ftp.agdsn.de/fdroid/repo/'
	'https://ftp.lysator.liu.se/pub/fdroid/repo/'
	'https://mirror.fcix.net/fdroid/repo/'
	'https://mirror.ossplanet.net/fdroid/repo/'
	)
TEST_FILE_PATH="index-v1.jar"
BEST_SERVER=$(bash <(curl -s https://raw.githubusercontent.com/GandharvJain/Scripts/master/bestServer.sh) $TEST_FILE_PATH ${MIRRORS[@]})
echo "[termux_recover.sh] Best server is $BEST_SERVER"

# Helper function to download and install apk from Fdroid
deployFdroidApp() {
	PACKAGE_NAME=$1
	FORCE_INSTALL=$2

	# Getting latest version number of app
	APP_VERSION=$(curl -s https://f-droid.org/api/v1/packages/$PACKAGE_NAME | jq -r '.suggestedVersionCode')
	APP_APK=$PACKAGE_NAME"_"$APP_VERSION.apk

	# Getting official app name
	APP_NAME=$(curl -s https://gitlab.com/fdroid/fdroiddata/-/raw/master/metadata/$PACKAGE_NAME.yml | awk '/AutoName/ {print $2}')

	# Downloading apk
	curl "$BEST_SERVER/$APP_APK" -o $PWD/$APP_APK

	echo "[termux_recover.sh] Downloaded $APP_APK"

	Set allow-external-apps to true in ~/.termux/termux.properties
	value="true"; key="allow-external-apps"; file="$HOME/.termux/termux.properties"; mkdir -p "$(dirname "$file")"; chmod 700 "$(dirname "$file")"; if ! grep -E '^'"$key"'=.*' $file &>/dev/null; then [[ -s "$file" && ! -z "$(tail -c 1 "$file")" ]] && newline=$'\n' || newline=""; echo "$newline$key=$value" >> "$file"; else sed -i'' -E 's/^'"$key"'=.*/'"$key=$value"'/' $file; fi

	# Installing apk
	if [[ ${FORCE_INSTALL,,} =~ ^(y|yes)$ ]]; then
		termux-open --view $APP_APK
	else
		termux-notification -t "Install $APP_NAME" --action "termux-open --view $PWD/$APP_APK" &
	fi

	# Set allow-external-apps to false in ~/.termux/termux.properties
	# value="false"; key="allow-external-apps"; file="$HOME/.termux/termux.properties"; mkdir -p "$(dirname "$file")"; chmod 700 "$(dirname "$file")"; if ! grep -E '^'"$key"'=.*' $file &>/dev/null; then [[ -s "$file" && ! -z "$(tail -c 1 "$file")" ]] && newline=$'\n' || newline=""; echo "$newline$key=$value" >> "$file"; else sed -i'' -E 's/^'"$key"'=.*/'"$key=$value"'/' $file; fi
}

# Install Termux:API
deployFdroidApp com.termux.api yes

echo "[termux_recover.sh] Waiting for Termux:API to install"

# Wait till Termux:API is installed
IS_ERROR="dummy_text"
TERMUX_API_AVAILABLE=false
while true; do
	IS_ERROR=$(termux-api-start 2>&1 1>/dev/null)
	if [[ -z $IS_ERROR ]]; then
		TERMUX_API_AVAILABLE=true
		break
	fi
	sleep 3
done

echo "[termux_recover.sh] Installed Termux:API"

# Ask user whether to install extra apps
CHOICE=""
while [[ -z $CHOICE ]]; do
	CHOICE=$(termux-dialog confirm -t "Termux Recover Script" -i "Download extra apps?" | jq -r ".text")
	sleep 3
done

if [[ $CHOICE = yes ]]; then
	# Install Termux:Widget
	deployFdroidApp com.termux.widget no
	# Install Termux:Styling
	deployFdroidApp com.termux.styling no
	# Create termux shortcut
	termux-notification -t "Create termux shortcuts (Install Termux:Widget first)" --action "am start -a android.intent.action.CREATE_SHORTCUT -n com.termux.widget/.TermuxCreateShortcutActivity" &
fi

echo "[termux_recover.sh] Decrypting and extracting Termux backup..."

# Decrypting and extracting termux backup
while true; do
	extracted=false
	if [[ $TERMUX_API_AVAILABLE = true ]]; then
		PASS=$(termux-dialog text -t 'Termux Backup Password' -p | jq -r '.text')
		gpg --batch --pinentry-mode loopback --passphrase $PASS -d $BACKUP_FILE | tar zx -C $TERMUX_FILES --recursive-unlink --preserve-permissions && extracted=true
	else
		gpg -d $BACKUP_FILE | tar zx -C $TERMUX_FILES --recursive-unlink --preserve-permissions && extracted=true
	fi
	# Break out of loop only if successfully extracted
	$extracted && break || sleep 3
done

# Resetting terminal
cd "$(pwd)"
source $HOME/.bashrc

# Append history to HISTFILE
history -a

echo "[termux_recover.sh] Finished Termux recovery"