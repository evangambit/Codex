from utils import *
import matplotlib.pyplot as plt
import numpy as np
import torch

# from comment2features import comment2features

class TokenListFile:
  def __init__(self, path):
    self.path = path
    if not os.path.exists(self.path):
      with open(self.path, 'w+') as f:
        f.write('')
    self.vals = []
    self.n = 0

  def add(self, id_, score):
    self.n += 1
    self.vals.append((id_, score))
    if len(self.vals) > 100:
      self.flush()

  def flush(self):
    lines = []
    for id_, score in self.vals:
      id_ = pad(np.base_repr(id_, 36).lower(), n=7, c='0')
      score = pad(np.base_repr(score, 36).lower(), n=7, c='0')
      lines.append(score + ' ' + id_)
    with open(self.path, 'a') as f:
      f.write('\n'.join(lines) + '\n')
    self.vals = []

argparser = argparse.ArgumentParser()
argparser.add_argument("--numTokens", type=int, default=16384)
argparser.add_argument("--score", type=str)
argparser.add_argument("--outdir", type=str)
argparser.add_argument("--force", '-f', action='store_true')
args = argparser.parse_args()

assert (args.outdir is not None) == (args.score is not None)

if os.path.exists(args.outdir):
  if args.force:
    shutil.rmtree(args.outdir)
  else:
    print(f'Path "{args.outdir}" already exists')
    exit(0)
os.mkdir(args.outdir)

assert args.score in ['new', 'old', 'score', 'depth']

# Score functions return an integer between [0, 36^7 - 1]
kMaxInt = 36**7 - 1
if args.score == 'new':
  def get_score(comment):
    return int(comment['created'])
elif args.score == 'old':
  def get_score(comment):
    return kMaxInt - int(comment['created'])
elif args.score == 'score':
  def get_score(comment):
    return (kMaxInt//2) - comment.get('score', 0)
elif args.score == 'depth':
  def get_score(comment):
    return int(comment['depth'])

lists = {
  'allposts': TokenListFile(pjoin(args.outdir, 'allposts.list'))
}
for i in range(args.numTokens):
  lists[i] = TokenListFile(pjoin(args.outdir, pad(hex(i)[2:], n=5, c='0') + '.list'))

conn = sqlite3.connect('comments.db')
c = conn.cursor()

c.execute('SELECT * FROM comments')
it = -1
for row in c:
  it += 1
  if it % 10000 == 0:
    print(it)
  id_, j = row
  comment = json.loads(j)
  if 'body_html' not in comment:
    continue

  score = get_score(comment)

  for token in comment['tokens'].split(' '):
    lists[h(token) % args.numTokens].add(id_, score)
  lists['allposts'].add(id_, score)

print('flushing')
for token in lists:
  lists[token].flush()

print('sorting')
for i, token in enumerate(lists):
  if i % 500 == 0:
    print(i, len(lists))
  l = lists[token]
  os.system(f'sort "{l.path}" -u -o "{l.path}"')

counts = {}
for k in lists:
  counts[k] = lists[k].n

with open(pjoin(args.outdir, 'counts.json'), 'w+') as f:
  json.dump(counts, f)

