#!/usr/bin/python3

import sys, os

def getAllWindows():
	windows = []
	for line in os.popen('wmctrl -pl'):
		fields = line.split()[:3]
		# panel? At least no real display
		if fields[1] == '-1':
			continue
		# 'windows' is a list where each element is [window id, window pid]
		windows.append([int(fields[0], 16), fields[2]])
	sorted_windows = sort(windows)
	return sorted_windows

def getWorkspaceApps():
	# List of open windows
	recent_windows = os.popen('xprop -root _NET_CLIENT_LIST_STACKING').read()
	recent_windows = list(map(lambda x:int(x, 16), recent_windows.replace(',', '').split()[4:]))
	curr_workspace = currentWorkspace()

	workspace_apps = []
	open_apps_pid = set()
	for line in os.popen('wmctrl -pl'):
		window_id, workspace_id, app_pid = line.split()[:3]
		window_id = int(window_id, 16)
		workspace_id = int(workspace_id)

		# panel? At least no real display
		if workspace_id == curr_workspace:
			if app_pid in open_apps_pid:
				win_idx = next(i for i, w in enumerate(workspace_apps) if w[1] == app_pid)
				if recent_windows.index(window_id) > recent_windows.index(workspace_apps[win_idx][0]):
					workspace_apps[win_idx][0] = window_id
				continue

			open_apps_pid.add(app_pid)
			# 'windows' is a list where each element is [window id, window pid]
			workspace_apps.append([window_id, app_pid])

	return list(zip(*workspace_apps))[0]

def currentWindow():
	return int(os.popen('xprop -root _NET_ACTIVE_WINDOW').read().split()[4], 16)

def currentWorkspace():
	return int(os.popen('xprop -root -notype  _NET_CURRENT_DESKTOP').read().split()[2])

def sort(windows):

	# requesting pids of favourite apps in desired order
	favourites_pids = os.popen('pidof Discord nautilus chrome sublime_text spotify teams okular-bin').read().strip().split()
	
	sortedWinIds = []
	unsortedWinIds = list(list(zip(*windows))[0])
	open_window_pids = list(list(zip(*windows))[1])

	# Sorting
	for pid in favourites_pids:
		if pid in open_window_pids:
			while pid in open_window_pids:
				sortedWinIds.append(unsortedWinIds.pop(open_window_pids.index(pid)))
				open_window_pids.remove(pid)

	return sortedWinIds + unsortedWinIds

if __name__ == '__main__':

	# print(repr(windows))
	# print(repr(curr_win))
	curr_win = currentWindow()
	if len(sys.argv) != 2 or sys.argv[1] not in ['win_left', 'win_right', 'app_left', 'app_right']:
		print('''
browserswitch option
option:
	win_left:   move one window to the left
	win_right:  move one window to the right
	app_left:   move one app to the left in current workspace
	app_right:  move one app to the right in current workspace
	help:   this help message
''')
		exit()

	option = sys.argv[1]
	if option == 'win_left':
		windows = getAllWindows()
		idx = windows.index(curr_win)
		newwin = windows[idx-1]

	elif option == 'win_right':
		windows = getAllWindows()
		idx = windows.index(curr_win)
		newwin = windows[(idx+1)%len(windows)]

	elif option == 'app_left':
		apps = getWorkspaceApps()
		idx = apps.index(curr_win)
		newwin = apps[idx-1]

	elif option == 'app_right':
		apps = getWorkspaceApps()
		idx = apps.index(curr_win)
		newwin = apps[(idx+1)%len(apps)]
	os.system('wmctrl -ia %s' % newwin)
