#!/home/gandharv/python-user/bin/python3
import requests
from bs4 import BeautifulSoup
from multiprocessing import Pool, Manager
import pdfkit as pk
from pypdf import PdfReader, PdfWriter
import io

codes = {
	"APC": [*range(1, 10), 236, *range(248, 252)],
	"APM": [*range(10, 19), 238],
	"APP": [*range(19, 28), 235, 245, 246, 247, 252],
	"BCE": [*range(28, 39), 227],
	"BME": [*range(39, 50), 228],
	"CER": [*range(50, 68), 229],
	"CHE": [*range(68, 78), 230],
	"CIV": [*range(78, 97), 231],
	"CSE": [*range(97, 114), 232],
	"ECE": [*range(114, 124), 233],
	"EEE": [*range(124, 143), 234],
	"MEC": [*range(143, 162), 239],
	"MET": [*range(162, 181), 240],
	"MIN": [*range(181, 200), 241],
	"PHE": [*range(200, 216), 242],
	"SMST": [*range(216, 227), 237],
	"INST_CRCS": [243],
	"HSS": [244],
}
department_code = "CSE"
section_ids = codes[department_code]

pdf_name = f'{department_code}_Syllabus_Booklet.pdf'

headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}

manager = Manager()
courses = manager.dict()

def pullPage(dept_code, sec_id):
	page_url = f"https://courses.iitbhu.ac.in/index.php?dept_code={dept_code}&sec_id={sec_id}"
	rawpage = requests.get(page_url,headers=headers)
	soup = BeautifulSoup(rawpage.content, 'lxml')
	output = []

	course_entries = soup.findAll("table")[1].findAll('tr')[1:]
	for c in course_entries:
		url = c.find("button")['onclick'].split('\'')[1]

		course_code = c.find("td").text
		course_name = c.find("td", {"align": False}).text.rstrip("+* ")
		name = course_code + ": " + course_name
		name = ' '.join(name.split()).replace('/', '|')

		if course_code in courses or course_name in courses:
			continue
		courses[course_code] = True
		courses[course_name] = True

		course_name_html = f"""
			<!DOCTYPE html>
			<html lang="en">
				<head>
					<style>
						html, body {{
							height: 98%;
							width: 100%;
						}}

						body {{
							display: table;
						}}

						.my-block {{
							text-align: center;
							display: table-cell;
							vertical-align: middle;
							font-size: 35px;
							font-weight: bold;
						}}
					</style>
				</head>
				<body>
					<div class="my-block">
					{name}
					</div>
				</body>
			</html>"""

		stream = io.BytesIO(pk.from_string(course_name_html))
		output.append((course_name, PdfReader(stream)))

		stream = io.BytesIO(pk.from_url(url))
		output.append((course_code, PdfReader(stream)))

		print(f"Downloaded {name}")
	return output

inputs = [(department_code, str(i)) for i in section_ids]

outputs = Pool(8).starmap(pullPage, inputs)

# print(courses)
print("Writing to PDF...")

writer = PdfWriter()
for output in outputs:
	for code, pdf in output:
		if code in courses:
			writer.append_pages_from_reader(pdf)
			del courses[code]

with open(pdf_name, 'wb') as f:
	writer.write(f)

print(f"Written to {pdf_name}")