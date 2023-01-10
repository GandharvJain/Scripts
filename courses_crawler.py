import requests
from bs4 import BeautifulSoup
import pdfkit

headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}

def pullPage(dept_code, sec_id):
	page_url = f"https://courses.iitbhu.ac.in/index.php?dept_code={dept_code}&sec_id={sec_id}"
	rawpage = requests.get(page_url,headers=headers)
	soup = BeautifulSoup(rawpage.content, 'lxml')

	courses = soup.findAll("table")[1].findAll('tr')[1:]
	for c in courses:
		url = str(c).split('\'')[1]

		course_code = c.find("td").text
		course_name = c.find("td", {"align": False}).text.rstrip("+* ")
		name = course_code + ": " + course_name
		name = ' '.join(name.split()).replace('/', '|')

		pdfkit.from_url(url, name)
		print(f"Downloaded {name}.pdf")

for i in range(97, 106):
	pullPage("CSE", str(i))