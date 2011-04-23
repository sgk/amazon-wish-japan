#!/usr/bin/python
#vim:fileencoding=utf-8

import urllib2
try:
  from flask import json
except:
  import json

GOOGLE_API_URL = 'https://www.googleapis.com/urlshortener/v1/url'

def google(url, apikey=None):
  api = GOOGLE_API_URL
  if apikey:
    api += '?key=' + apikey

  data = json.dumps({'longUrl': url})
  headers = {'Content-Type': 'application/json'}
  request = urllib2.Request(api, data, headers)
  response = urllib2.urlopen(request).read()
  response = json.loads(response)
  return response.get('id', None)

if __name__ == '__main__':
  import sys
  for url in sys.argv[1:]:
    print google(url)
