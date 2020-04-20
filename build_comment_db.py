from utils import *
import matplotlib.pyplot as plt
import numpy as np
from urllib.parse import urlparse

parser = MyHTMLParser()

if os.path.exists('comments.db'):
  os.remove('comments.db')

conn = sqlite3.connect('comments.db')
c = conn.cursor()

# We store strings as their hashes, since strings are stored as blobs which seems undesirable.
# On the brightside the two 'strings' here (author and thread) should be small enough that collisions
# should essentially never happen.
cols = [
  "id INTEGER PRIMARY KEY",
  "json string"
]
c.execute(f"CREATE TABLE comments ({', '.join(cols)}) WITHOUT ROWID")
conn.commit()

D = []

def get_tokens(text, links, json, parent, gparent, isthread, iscw):
  # Add comment's words to tokens.
  text = parser.text.lower()
  text = re.sub(r"[^\w\d]+", " ", text)
  tokens = set(text.strip().split(' '))
  if '' in tokens:
    tokens.remove('')
  for token in list(tokens):
    if token in bad:
      tokens.remove(token)

  # Add author to tokens
  if 'author' in comment:
    tokens.add(f'author:{comment["author"]}')

  date = datetime.fromtimestamp(comment['created_utc'])
  # Compute time since an 'epoch'.
  # time0:    1 day
  # time1:    4 day3
  # time2:   16 days
  # time3:   64 days
  # time4:  256 days
  dt = comment['created_utc'] // (kSecsPerDay * 2)
  for i in range(5):
    tokens.add('time{i}:' + str(dt))
    dt = dt // 4
  tokens.add(f'year:{date.year}')

  # Add CW indicator
  if 'culture_war_roundup' in thread['url']:
    tokens.add('misc:cw' if iscw else 'misc:notcw')

  if not isthread:
    tokens.add(f'depth:{min(json["depth"], 20)}')

  tokens.add(f'score:{comment.get("score", 0)}')

  domains = set()
  for link in parser.links:
    loc = urlparse(link).netloc
    if loc[:4] == 'www.':
      loc = loc[4:]
    domains.add(loc)
  for domain in domains:
    tokens.add(f'linksto:{domain}')
  
  if parent:
    if 'author' in parent:
      tokens.add(f'pauthor:{parent["author"]}')
    tokens.add(f'pscore:{parent.get("score", 0)}')

  if gparent:
    if 'author' in gparent:
      tokens.add(f'pauthor:{gparent["author"]}')
    tokens.add(f'pscore:{gparent.get("score", 0)}')

  return tokens

with open('bad.json', 'r') as f:
  bad = json.load(f)

ids = set()
allscores = []
for thread in threads():
  comments = thread['comments']

  id2comment = {}
  for comment in comments:
    id2comment[comment['id']] = comment

  for comment in comments:
    if 'body_html' not in comment:
      continue
    if comment['body'] == '[deleted]':
      continue
    if comment['body_html'] == '<div class="md"><p>[deleted]</p>\n</div>':
      continue
    parser.reset()
    parser.feed(comment['body_html'])
    parser.close()

    depth = 0
    parent = id2comment.get(comment['parent_id'][3:], None)
    gparent = None
    if parent:
      depth += 1
      while parent['parent_id'][3:] in id2comment:
        depth += 1
        parent = id2comment.get(parent['parent_id'][3:], None)
    comment['depth'] = depth

    links = parser.links
    alltext = parser.alltext

    iscw = ('culture_war_roundup' in thread['url'])

    tokens = get_tokens(parser.text, links, comment, parent, gparent, isthread=False, iscw=iscw)
    comment['tokens'] = ' '.join(tokens)

    allscores.append(comment.get('score', 0))

    # Save some space -- all this information is in body_html anyway
    del comment['body']

    id_ = int(comment['id'], 36)
    if id_ in ids:
      continue
    ids.add(id_)

    c.execute("INSERT INTO comments VALUES (?, ?)", [id_, json.dumps(comment)])

conn.commit()
