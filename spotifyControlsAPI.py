#!/usr/bin/env python3

import spotipy
import concurrent.futures
from os import popen
import sys
import time

MAX_PLAYLIST_ITEMS = 100
MAX_SAVED_TRACKS = 20
MAX_THREADS = 128
LAST_FETCHED_SLACK_MS = 1000

username = ''
playlist_id = ''

log_file = '/home/gandharv/Scripts/secrets/spotipyScript.log'
creds_file = '/home/gandharv/Scripts/secrets/spotify_creds.txt'
icon_green_tick = "/usr/share/icons/Yaru/256x256/actions/dialog-yes.png"
icon_red_cross = "/usr/share/icons/Yaru/256x256/actions/dialog-no.png"
icon_red_exclaimation = "/usr/share/icons/Yaru/256x256/emblems/emblem-important.png"

def notify(title="No title", message="", icon_path=""):
	print(title, ": ", message)
	popen(f'notify-send "{title}" "{message}" -i "{icon_path}"')

def getSpotipyInstance():
	global username
	global playlist_id
	# Spotify API credentials
	try:
		with open(creds_file) as f:
			creds = f.read().splitlines()
			client_id, client_secret, redirect_uri, username, *playlist_ids = creds

		# In case no playlist id is given or multiple are given
		playlist_id = playlist_ids[0] if playlist_ids else ""
	except FileNotFoundError:
		notify("Credentials file is missing!", "Aborting..", icon_red_exclaimation)
		exit(1)
	scope = 'playlist-modify-public playlist-modify-private user-read-currently-playing '
	scope += 'user-modify-playback-state user-read-playback-state '
	scope += 'user-library-read user-library-modify'

	# Spotify API user credentials
	token = spotipy.util.prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri)
	if token:
		# Create a Spotipy instance
		sp = spotipy.Spotify(auth=token)
		return sp
	else:
		notify(f"Can't get token for {username}")
		exit(1)

def getAllTrackURIs(sp, isPlaylist, playlist_id=""):
	if isPlaylist:
		total_count = int(sp.playlist(playlist_id, fields='tracks')['tracks']['total'])
		tracks = []
		start = 0
		step = MAX_PLAYLIST_ITEMS
	else:
		response = sp.current_user_saved_tracks(limit=MAX_SAVED_TRACKS)
		total_count = response['total']
		tracks = [track['track']['uri'] for track in response['items']]
		start = MAX_SAVED_TRACKS
		step = MAX_SAVED_TRACKS

	# Function executed in parallel
	def getTrackURIs(offset):
		if isPlaylist:
			temp_tracks = sp.playlist_tracks(playlist_id, 'items', MAX_PLAYLIST_ITEMS, offset)['items']
		else:
			temp_tracks = sp.current_user_saved_tracks(MAX_SAVED_TRACKS, offset)['items']
		return [track['track']['uri'] for track in temp_tracks]

	# Checking if playlist already contains track
	with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
		futures = []
		offsets = range(start, total_count, step)
		for fetched_tracks in executor.map(getTrackURIs, offsets):
			tracks.extend(fetched_tracks)
	return tracks

def playlistControls(option, force_action=False):
	sp = getSpotipyInstance()
	# Get the currently playing track information
	current_track = sp.current_user_playing_track()
	if current_track is None:
		notify("No device playing spotify!", "Aborting..", icon_red_exclaimation)
		exit(1)

	current_track_uri = current_track['item']['uri']
	current_track_name = current_track['item']['name']
	current_track_artists = ", ".join([artist['name'] for artist in current_track['item']['artists']])

	# Checking if latest data
	current_time_ms = time.time() // 0.001
	fetched_time_ms = int(current_track['timestamp'])
	song_progress_ms = int(current_track['progress_ms'])
	time_since_last_fetched_ms = current_time_ms - fetched_time_ms
	if not force_action and time_since_last_fetched_ms > song_progress_ms + LAST_FETCHED_SLACK_MS:
		notify("Fetched old data!", "Aborting..", icon_red_exclaimation)
		exit(1)

	# Ignore existence of track in playlist if user forces, may cause duplicates
	if not force_action:
		playlist_contains_track = current_track_uri in getAllTrackURIs(sp, True, playlist_id)

	# If option is add-to-playlist
	if option == 'add-to-playlist':
		# Adding track to saved tracks if not already added
		added_to_saved_tracks = False
		if force_action or not sp.current_user_saved_tracks_contains([current_track_uri])[0]:
			sp.current_user_saved_tracks_add([current_track_uri])
			added_to_saved_tracks = True

		# Add the current track to the playlist
		if force_action or not playlist_contains_track:
			sp.user_playlist_add_tracks(username, playlist_id, [current_track_uri])

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
	elif option == 'remove-from-playlist':
		# Removing track from saved tracks if already added
		removed_from_saved_tracks = False
		if force_action or sp.current_user_saved_tracks_contains([current_track_uri])[0]:
			sp.current_user_saved_tracks_delete([current_track_uri])
			removed_from_saved_tracks = True

		# Remove the current track from the playlist
		if force_action or playlist_contains_track:
			sp.user_playlist_remove_all_occurrences_of_tracks(username, playlist_id, [current_track_uri])

			title = "Removed from playlist"
			title += " and saved tracks" if removed_from_saved_tracks else ""
			message = f"'{current_track_name}' by '{current_track_artists}'"
			notify(title, message, icon_green_tick)
		# Not adding the track to avoid duplicates
		else:
			title = f"Track is not in the playlist"
			title += " and saved tracks" if not removed_from_saved_tracks else ""
			message = f"'{current_track_name}' by '{current_track_artists}'"
			notify(title, message, icon_red_cross)

def removeDuplicates(isPlaylist):
	sp = getSpotipyInstance()
	indexed_tracks = enumerate(getAllTrackURIs(sp, isPlaylist, playlist_id))
	seen = set()
	duplicates = dict()
	for index, track in indexed_tracks:
		duplicates.setdefault(track, []).append(index) if track in seen else seen.add(track)

	tracks_to_remove = [{"uri": track, "positions": indices} for track, indices in duplicates.items()]

	if len(tracks_to_remove) != 0:
		if isPlaylist:
			sp.user_playlist_remove_specific_occurrences_of_tracks(username, playlist_id, tracks_to_remove)
		else:
			sp.current_user_saved_tracks_delete(tracks_to_remove)
		with open(log_file, 'w') as f:
			print(*tracks_to_remove, file=f, sep='\n')
	print(*tracks_to_remove, sep='\n')

	tracks_were_removed = bool(tracks_to_remove)
	title = f"Removed duplicates from {'playlist' if isPlaylist else 'saved tracks'}"
	title = title if tracks_were_removed else "No duplicates"
	message = f"See {log_file} for details" if tracks_were_removed else "No tracks removed"
	notify(title, message, icon_green_tick if tracks_were_removed else icon_red_cross)

def playerControls(action, force_action=False):
	sp = getSpotipyInstance()
	playback_state = sp.current_playback()
	if playback_state is None:
		notify("No device playing spotify", "Aborting..", icon_red_exclaimation)
		exit(1)

	if action == 'next': sp.next_track()
	elif action == 'previous': sp.previous_track()
	elif playback_state['is_playing']: sp.pause_playback()
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
	play-pause:                     toggle playback
	next:                           go to next song
	previous:                       go to previous song
	add-to-playlist:                add current song to playlist
	remove-from-playlist:           remove current song from playlist
	remove-playlist-duplicates:     remove duplicate songs from playlist
	remove-saved-duplicates:        remove duplicate songs from saved tracks
	help:                           this help message
Supported options:
	-f:                        force addition to (or removal from) playlist
	                           (May create duplicates)
''')

if __name__ == '__main__':
	args = sys.argv
	if len(args) < 2:
		printHelp()
		exit(1)

	force_action = '-f' in args[1:]
	args.pop(args.index('-f')) if force_action else None

	option = args[1]
	if option in ['add-to-playlist', 'remove-from-playlist']:
		playlistControls(option, force_action)
	elif option in ['play-pause', 'next', 'previous']:
		playerControls(option, force_action)
	elif option in ['remove-playlist-duplicates', 'remove-saved-duplicates']:
		removeDuplicates(option == 'remove-playlist-duplicates')
	else:
		printHelp()