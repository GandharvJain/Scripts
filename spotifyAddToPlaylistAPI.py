#!/usr/bin/env python3
import spotipy
import concurrent.futures
from os import popen

def main():
	# Spotify API credentials
	with open('/home/gandharv/Scripts/spotify_creds.txt') as f:
		creds = f.read().splitlines()
		client_id, client_secret, redirect_uri, username, playlist_id = creds
	scope = 'playlist-modify-public user-read-currently-playing'

	# Spotify API user credentials
	token = spotipy.util.prompt_for_user_token(username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

	if token:
		# Create a Spotipy instance
		sp = spotipy.Spotify(auth=token)

		# Get the currently playing track information
		current_track = sp.current_user_playing_track()
		current_track_uri = current_track['item']['uri']
		current_track_name = current_track['item']['name']
		current_track_artists = ", ".join([artist['name'] for artist in current_track['item']['artists']])

		# Get size of playlist
		playlist_size = int(sp.playlist(playlist_id, fields='tracks')['tracks']['total'])

		def get_playlist_tracks(offset, track_uri):
			temp_tracks = sp.playlist_tracks(playlist_id, limit=100, offset=offset)['items']
			return any(track['track']['uri'] == track_uri for track in temp_tracks)

		playlist_contains_track = False
		with concurrent.futures.ThreadPoolExecutor() as executor:
			futures = []
			offset = 0
			while offset <= playlist_size:
				futures.append(executor.submit(get_playlist_tracks, offset, current_track_uri))
				offset += 100
			playlist_contains_track = any(future.result() for future in concurrent.futures.as_completed(futures))

		if not playlist_contains_track:
			# Add the current track to the playlist
			sp.user_playlist_add_tracks(username, playlist_id, [current_track_uri])
			print(f"Added '{current_track_name}' by '{current_track_artists}' to playlist!")
			popen(f"notify-send \"Added to playlist\" \"'{current_track_name}' by '{current_track_artists}'\"")
		else:
			print(f"Track '{current_track_name}' by '{current_track_artists}' is already in the playlist!")
			popen(f"notify-send \"Track is already in the playlist!\" \"'{current_track_name}' by '{current_track_artists}'\"")

	else:
		print(f"Can't get token for {username}")
		popen(f"notify-send \"Can\'t get token for {username}\"")

if __name__ == '__main__':
	main()