# -*- coding: utf-8 -*-
"""
FutureLearn Downloader
"""

import sys, os, errno
import requests
import json
import re

from tqdm import tqdm           # progress indicator for updates
from lxml import html
from bs4 import BeautifulSoup, NavigableString
import string                    # for punctuation in filenames
import youtube_dl

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup Variable
SIGNIN_URL          = 'https://www.futurelearn.com/sign-in'
PROGRAMME_PAGE_URL  = 'https://www.futurelearn.com/your-programs'
FUTURELEARN_URL     = 'https://www.futurelearn.com'

# Test Values
COURSE_RUN          = 1

defaultHeaders = {
	'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36',
	'content-type': 'application/json',
}

OP_DIR  = os.getenv('OP_DIR',  default='./Output/')

INCLUDE_TOC = False
DOWNLOAD_YOUTUBE = True
DOWNLOAD_PDF = True
DOWNLOAD_COLABS = True

# set username and password
email = os.getenv('FL_EMAIL', default='username@mail.dcu.ie')
password = os.getenv('FL_PASSWORD', default='')

# FutureLearn login dataset

login_data = {
	"authenticity_token" : "",
    "utf8": '✓',
	"return": '',
	"title": '',
	"email": email,
	"password": password,
	"remember_me": 0
}

# Login to futurelearn (no error checking, so check headers!)
fl_session = requests.Session()
fl_response = fl_session.get(SIGNIN_URL)

soup = BeautifulSoup(fl_response.content, 'lxml')

login_data['authenticity_token'] = soup.find("input", attrs={"name": "authenticity_token"})['value']
login_rsp = fl_session.post(SIGNIN_URL, data=login_data)

# If you cannot login, then quit at this stage
if login_rsp.status_code != 200:
	print('Cannot login using : ' + email)
	quit(-1)


# List the programmes that you are signed up to
programmeContent = fl_session.get(PROGRAMME_PAGE_URL)
programmeSoup = BeautifulSoup(programmeContent.content, 'lxml')

# list all programmes as [number][programmme name][programme id]
programmeList = []
for data in programmeSoup.find_all('h2', attrs={'class':'m-program-block__heading'}):
	for a in data.find_all('a'):
		programmeList.append([a['href'].split('/')[-2],
							  a.text.replace('\n',' ').strip()]) #for getting text between the link

for i in range(0,len(programmeList)):
	print(i+1,' : ', programmeList[i-1][1])

	# ask which programme to download

a = int(input('Enter Programme Number : ')) - 1

if ( a < len(programmeList)) and (a >= 0):
	
	a -= 1
else:
	print('invalid input')
	a = 0

print ('Setting programme to', programmeList[a][1])

course_id = programmeList[a][0]

# Now we have the programme - get the programme index
COURSE_URL='{}/{}/{}'.format(PROGRAMME_PAGE_URL,course_id, 1)

pageContent = fl_session.get(COURSE_URL)

# todo - split the index into 'Topics' to match the courses
soup = BeautifulSoup(pageContent.content, 'lxml')


### Ignore all this for getting index
programmeTitle = course_id

# Go through the courses / week / steps to find links to content
topicList = []
courseList = []

for data in soup.findAll('div', attrs={'class':'compactCard-wrapper_1nofF'}):
	COURSE_URL='{}/{}'.format(FUTURELEARN_URL,data.a['href'])
	# print(COURSE_URL)
	
	topicList.append(data.find('h4').text)
	
	### get courses
	courseContent = fl_session.get(COURSE_URL)
	courseSoup = BeautifulSoup(courseContent.content, 'lxml')

	### get the links to the number of weeks, and sort them
	for weeks in courseSoup.find_all(class_ ="RunProgress-item_2NUyR"):
		WEEK_URL = '{}/{}'.format(FUTURELEARN_URL,weeks.a.get('href'))
		weekContent = fl_session.get(WEEK_URL)
		courseSoup = BeautifulSoup(weekContent.content, 'lxml')
		for step in courseSoup.find_all(class_ ="m-composite-link"):
			# print(step.get('href')) 
			course = {}
			course['chapter'] = step.span.text
			course['title'] = step.find(class_ = "m-composite-link__primary").text
			course['link'] = step.get('href')
			courseList.append(course)


print('{} Steps Identified in {} Courses'.format(len(courseList), len(topicList)))
 

#now get a course and filter it
from tqdm import tqdm

COURSE_BASE='https://www.futurelearn.com'

outputHTMLBody = ""

# Initialise the local variables
videoList = []
ToCList = []
prevSection = 0 #reset chapter
currTopic = 0

# write the name of the course
outputHTMLTitle = '<h1>' + programmeTitle + '</h1>'

for currentCourse in tqdm(courseList):

	link = '{}{}'.format(COURSE_BASE, currentCourse['link'])
	# print(link)

	stepContent = fl_session.get(link,headers=defaultHeaders)
	stepSoup = BeautifulSoup(stepContent.content, 'lxml')
	
	
	# Now we have the content - clean it up
	#step 1: Store Video Links and Remove youtube
	videos = stepSoup.findAll('iframe',{'id':'ytplayer'})
	for video in videos:
		videoList.append(video['src'])
		video.decompose()
	
	# next stage is to find the content body, and give it a title based on the topic list
	stepContent = stepSoup.find('div',{'class':'u-typography-bold-intro'})
	#stepContent.prettify()
	if stepContent:
		currSection = int(currentCourse['chapter'].split('.')[0])
		if prevSection != currSection:
			if currSection == 1: # new topic
				outputHTMLBody += '<p style="page-break-before: always">'
				outputHTMLBody += '<h2>Course ' + str(currTopic+1) + ' - ' + topicList[currTopic] + '</h2>'
				currTopic += 1
			else:
				outputHTMLBody += '<p style="page-break-before: always">'
		else:
			outputHTMLBody += '<p>'

		outputHTMLBody += '<h3>' + currentCourse['chapter'] + '&emsp;' + currentCourse['title'] + '</h3>'
		outputHTMLBody += str(stepContent)
		ToCList.append(currentCourse)
		prevSection = currSection



# Strip all maths tags that don't work
outputHTMLSoup = BeautifulSoup(outputHTMLBody,'lxml')
def strip_tags(scriptSoup):
    #strip out all invalid math/tex
	for tag in scriptSoup.findAll('script', attrs={'type':'math/tex'}):
		s = ""
		for c in tag.contents:
			if not isinstance(c, NavigableString):
				c = strip_tags(unicode(c), invalid_tags)
			s += c
		tag.replaceWith(s)

	# strip out all Skillnet images
	for tag in scriptSoup.findAll('img',{'alt': re.compile(r'Skillnet Ireland')}):
		s = ""
		tag.replaceWith(s)
	
	return scriptSoup

for i in outputHTMLSoup.findAll('script', attrs={'type':'math/tex'}):
	newString = '\(' + (i.string) + '\)'
	i.string = newString

outputHTMLBody = str(strip_tags(outputHTMLSoup))

# Write HTML Body to output file
#outputFilename = currentCourse['chapter'] + '-' + os.path.basename(link) + '.html'
outputFilename = OP_DIR + course_id + '.html'
outputHTMLTitle = '<h1>' + programmeTitle + '</h1>'
print (outputFilename)

if not os.path.exists(OP_DIR):
	os.makedirs(OP_DIR)

file = open(outputFilename, "w", encoding='utf-8')

# Print Header Information

# Header for HTML Latex
latexHeader = """
  <html>
  <header>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
  <link rel="stylesheet" type="text/css" href="latex.css">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
  <script id="MathJax-script" async
	  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
  </script>
  <style>
  img{ max-width:600px; }
  @media print 
  {
	  @page {
		size: A4; /* DIN A4 standard, Europe */
		margin:0;
	  }
	  html, body {
		  width: 210mm;
		  /* height: 297mm; */
		  height: 282mm;
		  /* font-size: 11px; */
		  background: #FFF;
		  overflow:visible;
	  }
	  body {
		  padding-top:15mm;
	  }
  }
  </style>
  </header>
  <body>

  """

file.write(latexHeader)

file.write(outputHTMLTitle)
file.write(outputHTMLBody)

if INCLUDE_TOC:
	# List of Contents
	file.write('<p style="page-break-before: always"><h1>Table of Contents</h1>')
	for entry in ToCList:
			file.write('<br>' + entry['chapter'] + '&emsp;' + entry['title'])
  
# Finish File
file.write('</body></html>')

# Download all refernced youtube videos
# !pip install --upgrade youtube-dl
#video = stepSoup.findAll('iframe',{'id':'ytplayer'})[0]['src']
if DOWNLOAD_YOUTUBE:
	ydl_opts = {}
	with youtube_dl.YoutubeDL(ydl_opts) as ydl:
		for video in videoList:
			ydl.download([video])

if DOWNLOAD_PDF:
	bodySoup = BeautifulSoup(outputHTMLBody,'lxml')

	for result in bodySoup.find_all(lambda tag: tag.name in ['h3', 'div'] ):
		if result.name == 'h3':
			title = result.text

		for atag in result.findAll('a'):
			link = atag.get('href')
			if link.endswith('pdf'):
				sFilename = str(OP_DIR + title + '.pdf')
				remove_punctuation_map = dict((ord(char), None) for char in  string.punctuation)
				sFilename.translate(remove_punctuation_map)

        # Download the PDF Files from Programme
        print('Downloading' , sFilename, ' from ', link)

        try:
             myfile = requests.get(link,allow_redirects=True, verify=False)
             open(sFilename, 'wb').write(myfile.content)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
             print('Error downloading: ', sFilename)

#taken from this StackOverflow answer: https://stackoverflow.com/a/39225039
import requests

def download_file_from_google_drive(id, destination):
	URL = "https://docs.google.com/uc?export=download"

	session = requests.Session()

	response = session.get(URL, params = { 'id' : id }, stream = True)
	token = get_confirm_token(response)

	if token:
		params = { 'id' : id, 'confirm' : token }
		response = session.get(URL, params = params, stream = True)

	save_response_content(response, destination)    

def get_confirm_token(response):
	for key, value in response.cookies.items():
		if key.startswith('download_warning'):
			return value

	return None

def save_response_content(response, destination):
	CHUNK_SIZE = 32768

	with open(destination, "wb") as f:
		for chunk in response.iter_content(CHUNK_SIZE):
			if chunk: # filter out keep-alive new chunks
				f.write(chunk)

if DOWNLOAD_COLABS:
	colabList = []
	allTextSoup  = BeautifulSoup(outputHTMLBody, 'lxml')
	googleDriveLinks = allTextSoup.findAll('a')
	for colabLink in googleDriveLinks:
		current_link = colabLink.get('href')
		if 'drive.google.com' in current_link:
			colabList.append(current_link)
		#Sample google colab link: https://drive.google.com/open?id=1Um0HlegnHXVUHctZYJfcH3ctd_9CTfdU

	print('Downloading', len(colabList), 'Colabs')
	gFilenameNumber = 1
	for gFile in tqdm(colabList):
		if '=' in gFile:
			gFilename = 'Colab_' + course_id + '_' + f"{gFilenameNumber:03d}" + '.ipynb'
			download_file_from_google_drive(gFile.split('=')[1],'Colabs/' + gFilename)
			gFilenameNumber += 1


print("Complete")
