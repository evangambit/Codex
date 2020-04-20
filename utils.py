import argparse, array, hashlib, json, os, random, re, shutil, sqlite3
from datetime import datetime
from html.parser import HTMLParser

pjoin = os.path.join

def pad(t, n, c=' '):
  return max(n - len(t), 0) * c + t

class Hash64:
  def __init__(self):
    pass
  def __call__(self, x):
    h = hashlib.sha256()
    h.update(x.encode())
    return int(h.hexdigest()[-16:], 16) - (1<<63)
h = Hash64()

kSecsPerDay = 60 * 60 * 24  # 86,400
kSecsPerWeek = kSecsPerDay * 7

kUrlRegex = r"https?:\\/\\/(www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b([-a-zA-Z0-9()@:%_\\+.~#?&//=]*)"

class MyHTMLParser(HTMLParser):
  def reset(self):
    super().reset()
    self.blockquote = 0
    self.text = ''
    self.alltext = '' # Includes quoted text.
    self.links = set()

  def handle_starttag(self, tag, attrs):
    if tag == 'blockquote':
      self.blockquote += 1
    elif tag == 'a':
      href = [x for x in attrs if x[0] == 'href']
      self.links.add(href[0][1])

  def handle_endtag(self, tag):
    if tag == 'blockquote':
      self.blockquote -= 1

  def handle_data(self, data):
    isUrl = bool(re.match(kUrlRegex, data))
    self.alltext += data
    if self.blockquote == 0 and not isUrl:
      self.text += data

def threads():
  base = 'comments'
  for year in os.listdir(base):
    if not year.isdigit():
      continue
    for fn in os.listdir(pjoin(base, year)):
      if fn[-5:] != '.json':
        continue
      path = pjoin(base, year, fn)
      with open(pjoin(base, year, fn), 'r') as f:
        J = json.load(f)
      yield J
