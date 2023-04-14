#!/usr/bin/python3

from spotipy.util import prompt_for_user_token
from spotipy import Spotify
import concurrent.futures
from os import popen
import sys
import time
import json

# Numeric Constants
MAX_PLAYLIST_ITEMS = 100
MAX_SAVED_TRACKS = 20
MAX_THREADS = 64
LAST_FETCHED_SLACK_MS = 1000
REDUCE_API_CALLS = True

username = ""
playlist_id = ""

# File paths
tracks_file = "/home/gandharv/Scripts/secrets/tracks.json"
log_file = "/home/gandharv/Scripts/secrets/spotipy_script.log"
creds_file = "/home/gandharv/Scripts/secrets/spotify_creds.txt"
icon_green_tick = "/usr/share/icons/Yaru/256x256/actions/dialog-yes.png"
icon_red_cross = "/usr/share/icons/Yaru/256x256/actions/dialog-no.png"
icon_red_exclaimation = "/usr/share/icons/Yaru/256x256/emblems/emblem-important.png"

# DBus commands
dbus_ping_cmd = "dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.freedesktop.DBus.Peer.Ping"
dbus_toggle_cmd = "dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause"
dbus_prev_cmd = "dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Previous"
dbus_next_cmd = "dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Next"

def notify(title="No title", message="", icon_path=""):
	print(title, ": ", message)
	popen(f'''notify-send "{title}" "{message}" -i "{icon_path}"''')

def getSpotipyInstance():
	global username
	global playlist_id
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

	# Spotify API user credentials
	token = prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri)
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
		json.dump(json_dict, f, indent=4)

def getAllTrackURIs(sp, isPlaylist, playlist_id="", use_offline_tracks=False):
	# Loading tracks and snapshot id from json file
	old_snapshot_id, playlist_tracks, saved_tracks = loadJsonDict()

	if use_offline_tracks:
		return (old_snapshot_id, playlist_tracks, saved_tracks)

	if isPlaylist:
		playlist_info = sp.playlist(playlist_id, fields="tracks.total,snapshot_id")
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

def removeDuplicates(option):
	isPlaylist = option in ["remove-playlist-duplicates", "-rpd"]
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

def playerControls(action, force_action=False):
	sp = getSpotipyInstance()
	playback_state = sp.current_playback()
	# Check if spotify is connected by dbus
	dbus_is_connected = bool(popen(dbus_ping_cmd).read())

	if playback_state is None and not dbus_is_connected:
		notify("No device playing spotify", "Aborting..", icon_red_exclaimation)
		exit(1)

	if action in ["next", "-n"]:
		sp.next_track() if not dbus_is_connected else popen(dbus_next_cmd)
	elif action in ["previous", "-p"]:
		sp.previous_track() if not dbus_is_connected else popen(dbus_prev_cmd)
	# If action is play/pause:
	elif dbus_is_connected: popen(dbus_toggle_cmd)
	elif playback_state.get("is_playing", True): sp.pause_playback()
	else:
		try: sp.start_playback()
		except Exception as e1:
			# In private session 'is_playing' is always False but controls still work
			if force_action:
				try: sp.pause_playback()
				except Exception as e2: raise(e2)
			else: raise(e1)

def printHelp():
	print(f'''
Usage: {args[0]} [actions] [options]
Supported actions:
	-t,   play-pause:                    toggle playback
	-n,   next:                          go to next song
	-p,   previous:                      go to previous song
	-a,   add-to-playlist:               add current song to playlist
	-r,   remove-from-playlist:          remove current song from playlist
	-rpd, remove-playlist-duplicates:    remove duplicate songs from playlist
	-rsd, remove-saved-duplicates:       remove duplicate songs from saved tracks
	-h,   help:                          this help message
Extra options:
	-f:                                  force addition to (or removal from) playlist
	                                     (May create duplicates)
''')
	exit(1)

if __name__ == "__main__":
	args = sys.argv
	if not 1 < len(args) < 4:
		printHelp()

	force_action = "-f" in args
	if len(args) == 3:
		test = args.pop(args.index("-f")) if force_action else None
		if test is None: printHelp()

	option = args[1]
	if option in ["add-to-playlist", "-a", "remove-from-playlist", "-r"]:
		playlistControls(option, force_action)
	elif option in ["play-pause", "-t", "next", "-n", "previous", "-p"]:
		playerControls(option, force_action)
	elif option in ["remove-playlist-duplicates", "-rpd", "remove-saved-duplicates", "-rsd"]:
		removeDuplicates(option)
	else:
		printHelp()


# Add this to ~/.bash_completions for tab auto-complete in terminal:
'''
_spotifyControlsAPI.py()
{
	local cur prev words cword opts1 opts2
	_init_completion || return

	opts1a=(play-pause next previous add-to-playlist remove-from-playlist)
	opts1b=(-t -n -p -a -r)
	opts2a=(remove-playlist-duplicates remove-saved-duplicates help)
	opts2b=(-rpd -rsd -h)

	if [[ $cword -eq 1 ]]; then
		if [[ $cur == -* ]]; then
			COMPREPLY=( $(compgen -W "${opts1b[*]} ${opts2b[*]} -f" -- "$cur") )
		else
			COMPREPLY=( $(compgen -W "${opts1a[*]} ${opts2a[*]}" -- "$cur") )
		fi
		[[ $COMPREPLY ]] && return
	elif [[ $cword -eq 2 ]]; then
		if [[ $prev == '-f' ]]; then
			if [[ $cur == -* ]]; then
				COMPREPLY=( $(compgen -W "${opts1b[*]}" -- "$cur") )
			else
				COMPREPLY=( $(compgen -W "${opts1a[*]}" -- "$cur") )
			fi
			[[ $COMPREPLY ]] && return
		fi
		check=false
		for opt in "${opts1a[@]}" "${opts1b[@]}"; do
			[[ "$opt" == "$prev" ]] && check=true
		done
		if $check; then
			COMPREPLY=( $(compgen -W "-f" -- "$cur") )
			[[ $COMPREPLY ]] && return
		fi
	fi
} &&
complete -o nosort -F _spotifyControlsAPI.py spotifyControlsAPI.py
'''