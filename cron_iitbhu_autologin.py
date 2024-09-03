#!/home/gandharv/python-user/bin/python3

# Add this script to a scheduling system to run every x hours or so
import time
import getopt
import sys
from urllib import request, parse
import re

# Setting up params
ignore_last_login = False
username = '20124018'
login_link = 'http://192.168.249.1:1000/login?'
logout_link = 'http://192.168.249.1:1000/logout?'

secrets_path = '/home/gandharv/Scripts/secrets/'
last_login_file = secrets_path + 'lastLogin.txt'
wifi_pass_file = secrets_path + 'iitbhu_wifi_pass.txt'
with open(last_login_file) as f:
	last_login = int(f.readline().strip('\n'))

opts, args = getopt.getopt(sys.argv[1:], "f")
for opt, arg in opts:
	if opt in ['-f']:
		ignore_last_login = True

curr_time = time.strftime("%A %d %B %Y %T %Z", time.localtime())
print(f"Attempting relogin at {curr_time}")

# Skip relogin if recently logged in
time_since_login = int(time.time()) - last_login
login_cooldown = 4*60*60 - 5*60		#In seconds
if time_since_login < login_cooldown:
	print(f"Already logged in recently at {time.strftime("%A %d %B %Y %T %Z", time.localtime(last_login))}")
	if ignore_last_login:
		print("Ignoring last login..")
	else:
		sys.exit()

# Checking if connected to IIT (BHU)
try: 
	r = request.urlopen(login_link, timeout=0.5).read().decode('utf-8')
except:
	print("Not connected to the wifi IIT(BHU)!")
	sys.exit()

with open(wifi_pass_file) as f:
	password = f.readline().strip('\n')

print("Logging out..")
logout_output = request.urlopen(logout_link, timeout=3).read().decode('utf-8')
pattern = re.compile(r'name="magic"\s*value="(\w+)"')
groups = pattern.search(r)
magic = groups[1]

print("Logging in..")
try:
	data = parse.urlencode({'4Tredir': login_link, 'magic': magic, 'username': username, 'password': password}).encode()
	curl_output = request.urlopen('http://192.168.249.1:1000', timeout=3, data=data)
	print("Logged in!")
	with open(last_login_file, 'w') as f:
		f.write(str(int(time.time())))
except:
	print("Error logging in!")
	sys.exit()