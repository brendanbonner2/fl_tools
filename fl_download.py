# -*- coding: utf-8 -*-
"""FL_Download.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1-SJuJjAAp06cMN4Nt4jx0ObflAlrMlZe
"""

import sys, os, errno
import requests
import json

from tqdm import tqdm
from lxml import html
from bs4 import BeautifulSoup

# Setup Variable

SIGNIN_URL = 'https://www.futurelearn.com/sign-in'
PROGRAMME_PAGE_URL = 'https://www.futurelearn.com/your-programs'

# Test Values
COURSE_ID="data-analytics-and-data-mining"
COURSE_RUN=1

defaultHeaders = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36',
    'content-type': 'application/json',
}

TMP_DIR = os.getenv('TMP_DIR', default='./Output')
OP_DIR  = os.getenv('OP_DIR',  default='./Output')
DOWNLOAD_YOUTUBE = False

# set username and password
email = os.getenv('FL_EMAIL', default='username@mail.dcu.ie')
password = os.getenv('FL_PASSWORD', default='')
print('Using: ', email)

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

print(login_rsp)

# List the programmes that you are signed up to

# get programme page
programmeContent = fl_session.get(PROGRAMME_PAGE_URL)
programmeSoup = BeautifulSoup(programmeContent.content, 'lxml')

# list all programmes as [number][programmme name][programme id]

programmeList = []
for data in programmeSoup.find_all('h2', attrs={'class':'m-program-block__heading'}):
    #print(data)
    for a in data.find_all('a'):
        programmeList.append([a['href'].split('/')[-2],
                              a.text.replace('\n',' ').strip()]) #for getting text between the link

for i in range(0,len(programmeList)):
    print(i+1,' : ', programmeList[i-1][1])

    # ask which programme to download

print('Enter Programme Number:')
a = int(input()) - 1
if ( a < len(programmeList)) and (a >= 0):
    
    a -= 1
else:
    print('invalid input')
    a = 0

print ('Setting programme to', programmeList[a][1])

course_id = programmeList[a][0]
print(course_id)

# Now we have the programme - get the programme index
COURSE_URL='{}/{}/{}/index'.format(PROGRAMME_PAGE_URL,course_id, 1)
print(COURSE_URL)

pageContent = fl_session.get(COURSE_URL)

# todo - split the index into 'Topics' to match the courses

# Now break out the course weeks into links
soup = BeautifulSoup(pageContent.content, 'lxml')

for data in soup.find_all('div', attrs={'class':'m-heads-up-banner__text'}):
    for a in data.find_all('a'):
        programmeTitle = a.text #for getting text between the link

print(programmeTitle)

steps = soup.findAll('div',attrs={'class': 'm-overview__step-row'})

courseList = []
course = {
    'chapter':'',
    'title':''
}

for step in soup.findAll('div',attrs={'class': 'm-overview__step-row'}):
    course = {}
    course['chapter'] = step.span.text
    course['title'] = step.a.get_text()
    course['link'] = step.a['href']
    courseList.append(course)

print('{} Course Steps Identified'.format(len(courseList)))
    

# check the programms included:
topicList = []
for topiclist in soup.findAll('h2',attrs={'class': 'a-heading a-heading--exsmall'}):
  topic = topiclist.text.replace(programmeTitle + ': ','')
  topicList.append(topic)

#now get a course and filter it
from tqdm import tqdm

COURSE_BASE='https://www.futurelearn.com'

outputHTMLBody = ""

# Print Header Information

videoList = []
ToCList = []

# write the name of the course
outputHTMLTitle = '<h1>' + programmeTitle + '</h1>'


prevSection = 0 #reset chapter
currTopic = 0

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
    

    #print(stepSoup.title)
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


print("Complete")



# Write HTML Body to output file

#outputFilename = currentCourse['chapter'] + '-' + os.path.basename(link) + '.html'
outputFilename = course_id + '.html'
print (outputFilename)

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
          font-size: 11px;
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
outputHTMLTitle = '<h1>' + programmeTitle + '</h1>'

file.write(outputHTMLTitle)


file.write(outputHTMLBody)

# List of Contents
file.write('<p style="page-break-before: always"><h1>Table of Contents</h1>')
for entry in ToCList:
        file.write('<br>' + entry['chapter'] + '&emsp;' + entry['title'])
  
# Finish File
file.write('</body></html>')

print("Complete")

# Download all refernced youtube videos
# !pip install --upgrade youtube-dl
#video = stepSoup.findAll('iframe',{'id':'ytplayer'})[0]['src']
if DOWNLOAD_YOUTUBE:
    import youtube_dl

    ydl_opts = {}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for video in videoList:
            ydl.download([video])











