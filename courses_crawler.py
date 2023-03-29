#!/usr/bin/env python3
import requests
from unidecode import unidecode
from bs4 import BeautifulSoup
from multiprocessing import Pool
from fpdf import FPDF

headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}

def pullPage(dept_code, sec_id):
	page_url = f"https://courses.iitbhu.ac.in/index.php?dept_code={dept_code}&sec_id={sec_id}"
	rawpage = requests.get(page_url,headers=headers)
	soup = BeautifulSoup(rawpage.content, 'lxml')
	output = []
	courses = soup.findAll("table")[1].findAll('tr')[1:]
	for c in courses:
		url = str(c).split('\'')[1]

		course_code = c.find("td").text
		course_name = c.find("td", {"align": False}).text.rstrip("+* ")
		name = course_code + ": " + course_name
		name = ' '.join(name.split()).replace('/', '|')

		page = requests.get(url,headers=headers)
		sp = BeautifulSoup(page.content, 'lxml')
		body = sp.get_text('\n')
		output.append((name, body))
		print(f"Downloaded {name}")
	return output

inputs = [("CSE", str(i)) for i in range(97, 106)]

outputs = Pool(8).starmap(pullPage, inputs)
pdf = FPDF()
pdf.set_font('Arial')
for output in outputs:
	for name, body in output:
		pdf.add_page()
		pdf.set_font('', 'B', 14)
		pdf.write(8, name)
		pdf.set_font('', '', 10)
		pdf.write(8, '\n\n' + unidecode(body))

pdf.output('CSE_Syllabus_Booklet.pdf', 'F')
