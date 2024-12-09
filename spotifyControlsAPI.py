#!/home/gandharv/python-user/bin/python3

from spotipy.util import prompt_for_user_token
from spotipy import Spotify
import concurrent.futures
import subprocess
import sys
import time
import json
from pprint import pprint
import traceback

# Numeric Constants
MAX_PLAYLIST_ITEMS = 100
MAX_SAVED_TRACKS = 20
MAX_THREADS = 64
LAST_FETCHED_SLACK_MS = 10000
REDUCE_API_CALLS = True

username = ""
playlist_id = ""

# File paths
secrets_path = '/home/gandharv/Scripts/secrets/'
tracks_file = secrets_path + "tracks.json"
log_file = secrets_path + "spotipy_script.log"
creds_file = secrets_path + "spotify_creds.txt"
cache_file = secrets_path + ".cache-"
icon_green_tick = "/usr/share/icons/Yaru/256x256/actions/dialog-yes.png"
icon_red_cross = "/usr/share/icons/Yaru/256x256/actions/dialog-no.png"
icon_red_exclaimation = "/usr/share/icons/Yaru/256x256/emblems/emblem-important.png"

# DBus commands
dbus_prefix = ("dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.spotify", "/org/mpris/MediaPlayer2")
dbus_ping_cmd = dbus_prefix + ("org.freedesktop.DBus.Peer.Ping",)
dbus_toggle_cmd = dbus_prefix + ("org.mpris.MediaPlayer2.Player.PlayPause",)
dbus_prev_cmd = dbus_prefix + ("org.mpris.MediaPlayer2.Player.Previous",)
dbus_next_cmd = dbus_prefix + ("org.mpris.MediaPlayer2.Player.Next",)

def runCommand(command):
	completed_process = subprocess.run(command, capture_output=True)
	return completed_process.stderr, completed_process.stdout

def notify(title="No title", message="", icon_path=""):
	print(title)
	print(message) if message else None
	notifyCmd = ["notify-send", title, message, "-i", icon_path]
	error, output = runCommand(notifyCmd)

def getSpotipyInstance():
	global username
	global playlist_id
	global cache_file
	# Spotify API credentials
	try:
		with open(creds_file, 'r') as f:
			creds = f.read().splitlines()
			client_id, client_secret, redirect_uri, username, *playlist_ids = creds

		# In case no playlist id is given or multiple are given
		playlist_id = playlist_ids[0] if playlist_ids else ""
	except FileNotFoundError:
		notify("Credentials file is missing!", "Aborting..", icon_red_exclaimation)
		exit(1)
	scope = "playlist-modify-public playlist-modify-private user-read-currently-playing "
	scope += "user-modify-playback-state user-read-playback-state "
	scope += "user-library-read user-library-modify"
	cache_file += username

	# Spotify API user credentials
	token = prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri, cache_file)
	if token:
		# Create a Spotipy instance
		sp = Spotify(auth=token)
		return sp
	else:
		notify(f"Can't get token for {username}")
		exit(1)

def loadJsonDict():
	json_dict = dict()
	try:
		with open(tracks_file, 'r') as f:
			json_dict = json.load(f)
	except:
		pass
	old_snapshot_id = json_dict.get("snapshot_id", "")
	old_playlist_tracks = json_dict.get("playlist_tracks", [])
	old_saved_tracks = json_dict.get("saved_tracks", [])
	return (old_snapshot_id, old_playlist_tracks, old_saved_tracks)

def saveJsonDict(new_snapshot_id, new_playlist_tracks, new_saved_tracks):
	json_dict = {
		"snapshot_id": new_snapshot_id,
		"playlist_tracks": new_playlist_tracks,
		"saved_tracks": new_saved_tracks
	}
	with open(tracks_file, 'w') as f:
		json.dump(json_dict, f, indent='\t')

def getAllTrackURIs(sp, isPlaylist, playlist_id="", use_offline_tracks=False):
	# Loading tracks and snapshot id from json file
	old_snapshot_id, playlist_tracks, saved_tracks = loadJsonDict()

	if use_offline_tracks:
		return (old_snapshot_id, playlist_tracks, saved_tracks)

	if isPlaylist:
		playlist_info = sp.playlist(playlist_id, fields="snapshot_id,tracks.total")
		total_count = playlist_info["tracks"]["total"]
		curr_snapshot_id = playlist_info["snapshot_id"]
		# Ceiling function:
		num_api_calls = -(-total_count // MAX_PLAYLIST_ITEMS)

		# Return loaded tracks if playlist wasn't updated
		if total_count == len(playlist_tracks) and curr_snapshot_id == old_snapshot_id:
			if num_api_calls > MAX_THREADS or REDUCE_API_CALLS:
				offset = total_count - MAX_PLAYLIST_ITEMS
				items = sp.playlist_tracks(playlist_id, "items.track(uri)", MAX_PLAYLIST_ITEMS, offset)["items"]
				tracks = [track["track"]["uri"] for track in items]
				if tracks == playlist_tracks[-MAX_PLAYLIST_ITEMS:]:
					return (curr_snapshot_id, playlist_tracks, saved_tracks)

		tracks = []
		start = 0
		step = MAX_PLAYLIST_ITEMS
	else:
		response = sp.current_user_saved_tracks(limit=MAX_SAVED_TRACKS)
		total_count = response["total"]
		# There is no snapshot_id for saved tracks, it's here for return value
		curr_snapshot_id = old_snapshot_id
		tracks = [track["track"]["uri"] for track in response["items"]]
		# Return loaded tracks if the 20 most recently added tracks are same
		if total_count == len(saved_tracks) and tracks == saved_tracks[:len(tracks)]:
			return (curr_snapshot_id, playlist_tracks, saved_tracks)

		start = MAX_SAVED_TRACKS
		step = MAX_SAVED_TRACKS

	# Function executed in parallel
	def getTrackURIs(offset):
		if isPlaylist:
			temp_tracks = sp.playlist_tracks(playlist_id, "items.track(uri)", MAX_PLAYLIST_ITEMS, offset)["items"]
		else:
			temp_tracks = sp.current_user_saved_tracks(MAX_SAVED_TRACKS, offset)["items"]
		return [track["track"]["uri"] for track in temp_tracks]

	# Checking if playlist already contains track
	with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
		futures = []
		offsets = range(start, total_count, step)
		for fetched_tracks in executor.map(getTrackURIs, offsets):
			tracks.extend(fetched_tracks)
	return (curr_snapshot_id,) + ((tracks, saved_tracks) if isPlaylist else (playlist_tracks, tracks))

def playlistControls(option, force_action=False):
	sp = getSpotipyInstance()
	# Get the currently playing track information
	current_track = sp.current_user_playing_track()
	if current_track is None:
		notify("No device playing spotify!", "Aborting..", icon_red_exclaimation)
		exit(1)

	current_track_uri = current_track["item"]["uri"]
	current_track_name = current_track["item"]["name"]
	current_track_artists = ", ".join([artist["name"] for artist in current_track["item"]["artists"]])

	# Checking if latest data
	current_time_ms = time.time() // 0.001
	fetched_time_ms = int(current_track["timestamp"])
	song_progress_ms = int(current_track["progress_ms"])
	time_since_last_fetched_ms = current_time_ms - fetched_time_ms
	if not force_action and time_since_last_fetched_ms > song_progress_ms + LAST_FETCHED_SLACK_MS:
		notify("Fetched old data!", "Aborting..", icon_red_exclaimation)
		exit(1)

	curr_snapshot_id, playlist_tracks, saved_tracks = getAllTrackURIs(sp, True, playlist_id, force_action)

	# Ignore existence of track in playlist if user forces, may cause duplicates
	if not force_action:
		playlist_contains_track = current_track_uri in playlist_tracks

	# If option is add-to-playlist
	if option in ["add-to-playlist", "-a"]:
		# Adding track to saved tracks if not already added
		added_to_saved_tracks = False
		if not sp.current_user_saved_tracks_contains([current_track_uri])[0]:
			added_to_saved_tracks = True
			sp.current_user_saved_tracks_add([current_track_uri])
			# Adding to offline list of saved tracks
			saved_tracks.insert(0, current_track_uri)

		# Add the current track to the playlist
		if force_action or not playlist_contains_track:
			response = sp.user_playlist_add_tracks(username, playlist_id, [current_track_uri])
			curr_snapshot_id = response["snapshot_id"]
			# Adding to offline list of playlist tracks
			playlist_tracks.append(current_track_uri)

			title = "Added to playlist"
			title += " and saved tracks" if added_to_saved_tracks else ""
			message = f"'{current_track_name}' by '{current_track_artists}'"
			notify(title, message, icon_green_tick)
		# Not adding the track to avoid duplicates
		else:
			title = "Track is already in the playlist"
			title += " and saved tracks" if not added_to_saved_tracks else ""
			message = f"'{current_track_name}' by '{current_track_artists}'"
			notify(title, message, icon_red_cross)

	# If option is remove-from-playlist
	elif option in ["remove-from-playlist", "-r"]:
		# Removing track from saved tracks if already added
		removed_from_saved_tracks = False
		if sp.current_user_saved_tracks_contains([current_track_uri])[0]:
			removed_from_saved_tracks = True
			sp.current_user_saved_tracks_delete([current_track_uri])
			# Removing all occurrences from offline list of saved tracks
			saved_tracks = [track for track in saved_tracks if track != current_track_uri]

		# Remove the current track from the playlist
		if force_action or playlist_contains_track:
			response = sp.user_playlist_remove_all_occurrences_of_tracks(username, playlist_id, [current_track_uri])
			curr_snapshot_id = response["snapshot_id"]
			# Removing all occurrences from offline list of playlist tracks
			playlist_tracks = [track for track in playlist_tracks if track != current_track_uri]

			title = "Removed from playlist"
			title += " and saved tracks" if removed_from_saved_tracks else ""
			message = f"'{current_track_name}' by '{current_track_artists}'"
			notify(title, message, icon_green_tick)
		# Not adding the track to avoid duplicates
		else:
			title = "Track is not in the playlist"
			title += " and saved tracks" if not removed_from_saved_tracks else ""
			message = f"'{current_track_name}' by '{current_track_artists}'"
			notify(title, message, icon_red_cross)

	saveJsonDict(curr_snapshot_id, playlist_tracks, saved_tracks)

def removeDuplicates(options):
	option = options[0] if options else "playlist"
	if option not in ["playlist", "saved"]:
		notify("Invalid options", "Aborting..", icon_red_exclaimation)
		exit(1)

	isPlaylist = bool(option == "playlist")
	sp = getSpotipyInstance()

	curr_snapshot_id, playlist_tracks, saved_tracks = getAllTrackURIs(sp, isPlaylist, playlist_id)
	indexed_tracks = list(enumerate(playlist_tracks if isPlaylist else saved_tracks))
	seen = set()
	duplicates = dict()
	for index, track in indexed_tracks:
		duplicates.setdefault(track, []).append(index) if track in seen else seen.add(track)

	indices_to_remove = set(indx for indcs in duplicates.values() for indx in indcs)

	tracks_were_removed = False
	if len(duplicates) != 0:
		tracks_were_removed = True
		if isPlaylist:
			tracks_to_remove = [{"uri": track, "positions": indices} for track, indices in duplicates.items()]
			curr_snapshot_id = sp.user_playlist_remove_specific_occurrences_of_tracks(username, playlist_id, tracks_to_remove)
			curr_snapshot_id = curr_snapshot_id["snapshot_id"]
			# Removing from offline list of playlist tracks
			playlist_tracks = [trk for i, trk in indexed_tracks if i not in indices_to_remove]
		else:
			tracks_to_remove = list(duplicates.keys())
			# Song reuploads may cause newest version to appear as not liked which
			# on liking results in multiple entries of same song with different URIs
			sp.current_user_saved_tracks_delete(tracks_to_remove)
			# Removing from offline list of saved tracks
			saved_tracks = [trk for i, trk in indexed_tracks if i not in indices_to_remove]
			# Adding it back in
			sp.current_user_saved_tracks_add(tracks_to_remove)
			# Adding to offline list of saved tracks
			saved_tracks = tracks_to_remove + saved_tracks

		with open(log_file, 'w') as f:
			print(*tracks_to_remove, file=f, sep='\n')
		print(*tracks_to_remove, sep='\n')

	title = "Removed duplicates from " if tracks_were_removed else "No duplicates in "
	title += "playlist" if isPlaylist else "saved tracks"
	message = f"See {log_file} for details" if tracks_were_removed else "No tracks removed"
	notify(title, message, icon_green_tick if tracks_were_removed else icon_red_cross)

	saveJsonDict(curr_snapshot_id, playlist_tracks, saved_tracks)

def extraPlaybackControls(action, options=list()):
	sp = getSpotipyInstance()
	playback_state = sp.current_playback()

	if playback_state is None:
		notify("No device playing spotify", "Aborting..", icon_red_exclaimation)
		exit(1)

	shuffle_status = playback_state.get("shuffle_state")
	repeat_status = playback_state.get("repeat_state", "off")
	option1 = options[0] if options else None

	if action in ["shuffle", "-s"]:
		if option1 is None:
			option1 = "off" if shuffle_status else "on"

		if option1 == "on":
			sp.shuffle(True)
			notify("Turned shuffle on")
		elif option1  == "off":
			sp.shuffle(False)
			notify("Turned shuffle off")
		else:
			notify("Invalid options", "Aborting..", icon_red_exclaimation)

	elif action in ["loop", "repeat", "-l"]:
		if option1 is None:
			valid_options = ["track", "context", "off"]
			next_index = (valid_options.index(repeat_status) + 1) % len(valid_options)
			option1 = valid_options[next_index]

		if option1 in ["one", "track"]:
			sp.repeat("track")
			notify("Turned repeat on for track")
		elif option1 in ["all", "context"]:
			sp.repeat("context")
			notify("Turned repeat on for playlist")
		elif option1 == "off":
			sp.repeat("off")
			notify("Turned repeat off")
		else:
			notify("Invalid options", "Aborting..", icon_red_exclaimation)

def transportControls(action):
	# Check if spotify is connected by dbus
	error, output = runCommand(dbus_ping_cmd)
	dbus_is_connected = not bool(error)
	if dbus_is_connected:
		if action in ["next", "-n"]:
			err, out = runCommand(dbus_next_cmd)
		elif action in ["previous", "-p"]:
			err, out = runCommand(dbus_prev_cmd)
		# If action is play/pause:
		else:
			err, out = runCommand(dbus_toggle_cmd)
		exit(0)

	sp = getSpotipyInstance()

	playback_state = sp.current_playback()
	if playback_state is None:
		notify("No device playing spotify", "Aborting..", icon_red_exclaimation)
		exit(1)

	if action in ["next", "-n"]:
		sp.next_track()
	elif action in ["previous", "-p"]:
		sp.previous_track()
	# If action is play/pause:
	else:
		if playback_state["is_playing"]:
			sp.pause_playback()
		elif playback_state["device"]["is_private_session"]:
			try: sp.pause_playback()
			except: sp.start_playback()
		else:
			sp.start_playback()

def getCurrentPlayback(options=list()):
	sp = getSpotipyInstance()
	option1 = options[0] if options else None

	try:
		playback_state = sp.current_playback(market=option1)
	except Exception as e:
		notify("Error", e.msg, icon_red_exclaimation)
		raise(e)

	if playback_state is None:
		notify("No device playing spotify", "Aborting..", icon_red_exclaimation)
		exit(1)

	pprint(playback_state)

def printHelp(name):
	print(f'''
Usage: {name} [ACTION] [OPTIONS]

Supported actions:
-------------------------------------------------------------------------------------------
Short Long                    Options            Description
-------------------------------------------------------------------------------------------
-t    play-pause                                 Toggle playback
-n    next                                       Go to next song
-p    previous                                   Go to previous song
-a    add-to-playlist                            Add current song to playlist
-r    remove-from-playlist                       Remove current song from playlist
-s    shuffle                 on, off            Turn shuffle on or off (Default: toggle)
-l    loop                    one, all, off      Repeat current song or playlist or turn
                                                 it off (Default: cycle through options)
-d    remove-duplicates       playlist, saved    Remove duplicate songs (Default: playlist)
-i    info                    [Market]           Get information about current playback
-h    help                                       Show this help message
-f                                               Force addition to (or removal from)
                                                 playlist (May create duplicates)
''')
	exit(1)

if __name__ == "__main__":
	args = sys.argv
	if "-f" in args:
		force_action = True
		args.pop(args.index("-f"))
	else: force_action = False

	if not 1 < len(args) < 4:
		printHelp(args[0])

	option, *extra_options = args[1:]
	extra_options = [opt.lower() for opt in extra_options]

	try:
		if option in ["info", "-i"]:
			getCurrentPlayback(extra_options)
		elif option in ["add-to-playlist", "-a", "remove-from-playlist", "-r"]:
			playlistControls(option, force_action)
		elif option in ["play-pause", "-t", "next", "-n", "previous", "-p"]:
			transportControls(option)
		elif option in ["shuffle", "-s", "loop", "repeat", "-l"]:
			extraPlaybackControls(option, extra_options)
		elif option in ["remove-duplicates", "-d"]:
			removeDuplicates(extra_options)
		else:
			printHelp(args[0])
	except Exception as e:
		notify("An error occured!", "Aborting..", icon_red_exclaimation)
		with open(log_file, 'w') as f:
			print(traceback.format_exc(), file=f)
		raise(e)



# Add this to ~/.bash_completions for tab auto-complete in terminal:
'''
_spotifyControlsAPI.py()
{
	local cur prev words cword
	_init_completion || return

	declare -A opts_l=(
		[play-pause]=1 [next]=1 [previous]=1
		[add-to-playlist]=1 [remove-from-playlist]=1
		[shuffle]=1 [loop]=1 [remove-duplicates]=1 [info]=1 [help]=1
	)
	declare -A opts_s=(
		[-t]=1 [-n]=1 [-p]=1 [-a]=1 [-r]=1 [-s]=1 [-l]=1 [-d]=1 [-i]=1 [-h]=1
	)
	declare -A opts_l_force=(
		[add-to-playlist]=1 [remove-from-playlist]=1
	)
	declare -A opts_s_force=(
		[-a]=1 [-r]=1
	)
	declare -A opts_l_extra=(
		[shuffle]=1 [loop]=1 [repeat]=1 [remove-duplicates]=1 [info]=1
	)
	declare -A opts_s_extra=(
		[-s]=1 [-l]=1 [-d]=1 [-i]=1
	)
	market=(
		AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW 
	)

	if [[ $cword -eq 1 ]]; then
		if [[ $cur == -* ]]; then
			COMPREPLY=( $(compgen -W "${!opts_s[*]} -f" -- "$cur") )
		else
			COMPREPLY=( $(compgen -W "${!opts_l[*]}" -- "$cur") )
		fi
		[[ $COMPREPLY ]] && return
	elif [[ $cword -ge 2 ]]; then
		if [[ $prev == '-f' ]]; then
			if [[ $cur == -* ]]; then
				COMPREPLY=( $(compgen -W "${!opts_s_force[*]}" -- "$cur") )
			else
				COMPREPLY=( $(compgen -W "${!opts_l_force[*]}" -- "$cur") )
			fi
			[[ $COMPREPLY ]] && return
		fi
		if [[ ( "${words[*]} " != *' -f '* ) && ( -n ${opts_l_force[$prev]} || -n ${opts_s_force[$prev]} ) ]]; then
			COMPREPLY=( $(compgen -W "-f" -- "$cur") )
		fi
		if [[ -n ${opts_l_extra[$prev]} || -n ${opts_s_extra[$prev]} ]]; then
			if [[ $prev == '-s' || $prev == 'shuffle' ]]; then
				COMPREPLY+=( $(compgen -W "on off" -- "$cur") )
			elif [[ $prev == '-l' || $prev == 'loop' || $prev == 'repeat' ]]; then
				COMPREPLY+=( $(compgen -W "one all off" -- "$cur") )
			elif [[ $prev == '-d' || $prev == 'remove-duplicates' ]]; then
				COMPREPLY+=( $(compgen -W "playlist saved" -- "$cur") )
			elif [[ $prev == '-i' || $prev == 'info' ]]; then
				COMPREPLY+=( $(compgen -W "${market[*]}" -- "$cur") )
			fi
		fi
		[[ $COMPREPLY ]] && return
	fi
} &&
complete -o nosort -F _spotifyControlsAPI.py spotifyControlsAPI.py
'''
