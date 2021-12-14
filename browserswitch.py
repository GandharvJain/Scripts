#!/usr/bin/python

import sys, os

def getlist():
    windows = []
    for line in os.popen('wmctrl -pl'):
        fields = line.split()[:3]
        if fields[1] == '-1': # panel? At least no real display
            continue
        windows.append([int(fields[0], 16), fields[2]]) # 'windows' is a list where each element is [window id, window pid]
    sorted_windows = sort(windows)
    return sorted_windows

def currentwin():
    return int(os.popen('xdotool getactivewindow').read().strip())

def sort(windows):

    # requesting pids of favourite apps in desired order
    favourites_pids = os.popen('pidof nautilus-desktop Discord nautilus chrome sublime_text spotify gnome-terminal-server teams-insiders okular-bin').read().strip().split()
    
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

    windows = getlist()[0:]
    current = currentwin()
    # print(repr(windows))
    # print(repr(current))
    index = windows.index(current)
    if len(sys.argv) != 2 or sys.argv[1] not in ['left', 'right']:
        print('''
browserswitch option
option:
    left:   move one to the left
    right:  move one to the right
    help:   this help message
''')
        exit()
    option = sys.argv[1]
    if option == 'left':
        # if index == 1:
        #     index = 0
        newwin = windows[index-1]
    else:
        if index+1 == len(windows):
            # the rightmost window, switch to the leftmost window, not desktop
            newwin = windows[0]
        else:
            # normal behaviour
            newwin = windows[index+1]
    os.system('wmctrl -ia %s' % hex(newwin))
