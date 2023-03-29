#!/usr/bin/env python3

import spotipy
import concurrent.futures
from os import popen
import sys

username = ''
playlist_id = ''

def getSpotipyInstance():
	global username
	global playlist_id
	# Spotify API credentials
	with open('/home/gandharv/Scripts/secrets/spotify_creds.txt') as f:
		creds = f.read().splitlines()
		client_id, client_secret, redirect_uri, username, playlist_id = creds
	scope = 'playlist-modify-public user-read-currently-playing '
	scope += 'user-modify-playback-state user-read-playback-state '
	scope += 'user-library-read user-library-modify'

	# Spotify API user credentials
	token = spotipy.util.prompt_for_user_token(username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
	if token:
		# Create a Spotipy instance
		sp = spotipy.Spotify(auth=token)
		return sp
	else:
		print(f"Can't get token for {username}")
		popen(f"notify-send \"Can\'t get token for {username}\"")
		exit(1)

def addToPlaylist():
	sp = getSpotipyInstance()
	# Get the currently playing track information
	current_track = sp.current_user_playing_track()
	current_track_uri = current_track['item']['uri']
	current_track_name = current_track['item']['name']
	current_track_artists = ", ".join([artist['name'] for artist in current_track['item']['artists']])

	# Get size of playlist
	playlist_size = int(sp.playlist(playlist_id, fields='tracks')['tracks']['total'])

	# Function executed in parallel
	def get_playlist_tracks(offset, track_uri):
		temp_tracks = sp.playlist_tracks(playlist_id, limit=100, offset=offset)['items']
		return any(track['track']['uri'] == track_uri for track in temp_tracks)

	# Checking if playlist already contains track
	playlist_contains_track = False
	with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
		futures = []
		offset = 0
		while offset <= playlist_size:
			futures.append(executor.submit(get_playlist_tracks, offset, current_track_uri))
			offset += 100
		playlist_contains_track = any(future.result() for future in concurrent.futures.as_completed(futures))

	# Adding track to saved tracks if not already added
	added_to_saved_tracks = False
	if not sp.current_user_saved_tracks_contains([current_track_uri])[0]:
		sp.current_user_saved_tracks_add([current_track_uri])
		added_to_saved_tracks = True

	container = "playlist"
	if not playlist_contains_track:
		# Add the current track to the playlist
		sp.user_playlist_add_tracks(username, playlist_id, [current_track_uri])

		if added_to_saved_tracks:
			container += " and saved tracks"
		title = f"Added to {container}"
		message = f"'{current_track_name}' by '{current_track_artists}'"
		icon_path = "/usr/share/icons/Yaru/256x256/actions/dialog-yes.png"
		popen(f'notify-send "{title}" "{message}" -i {icon_path}')
		print(title, ": ", message)

	else:
		# Not adding the track to avoid duplicates
		if not added_to_saved_tracks:
			container += " and saved tracks"
		title = f"Track is already in the {container}"
		message = f"'{current_track_name}' by '{current_track_artists}'"
		icon_path = "/usr/share/icons/Yaru/256x256/actions/dialog-no.png"
		popen(f'notify-send "{title}" "{message}" -i {icon_path}')
		print(title, ": ", message)

def playerControl(action):
	sp = getSpotipyInstance()
	if action == 'next':
		sp.next_track()
	elif action == 'previous':
		sp.previous_track()
	else:
		if sp.current_playback()['is_playing']:
			sp.pause_playback()
		else:
			sp.start_playback()		

if __name__ == '__main__':
	if len(sys.argv) != 2 or sys.argv[1] not in ['play-pause', 'next', 'previous', 'add-to-playlist']:
		print(f'''
Usage: {sys.argv[0]} options
Supported options:
	play-pause:   move one window to the left
	next:  move one window to the right
	previous:   move one app to the left in current workspace
	add-to-playlist:  move one app to the right in current workspace
	help:   this help message
''')
		exit()

	option = sys.argv[1]
	if option == 'add-to-playlist':
		addToPlaylist()
	else:
		playerControl(option)