import json, os, sys, time
from datetime import datetime
from utils import *
pjoin = os.path.join

from union import Intersection, Union, FileIterator

dirname = 'score'
kNumTokens = 16384

with open(pjoin('index', dirname, 'counts.json'), 'r') as f:
  counts = json.load(f)

def _words2tokens(words):
  # Filter out ridiculously common words.  We primarily remove
  # these to keep the index size reasonable.
  with open('bad.json', 'r') as f:
    bad = json.load(f)
  words = [t for t in set(words) if t not in bad]

  tokens = [h(t) % kNumTokens for t in words]
  tokens = [pad(hex(t)[2:], n=5, c='0') for t in tokens]
  tokens = list(tokens)

  print(tokens)

  # If there are more than 12 tokens, drop the most common.
  # 16 is probably too large if most tokens are rare, but
  # this is the best case so we ignore it.  In the worst case
  # all tokens are very common, so we'd rather err on the side
  # of using too many tokens.
  if len(tokens) > 12:
    T = []
    for token in tokens:
      T.append((counts[token + '.list'], token))
    T.sort()
    tokens = [t[1] for t in T[:12]]
  if len(tokens) == 0:
    tokens = ['allposts']
  
  return tokens

class ListFetcher:
  def __init__(self, dirname, words):
    self.files = []
    for token in _words2tokens(words):
      self.files.append(
        FileIterator(pjoin(dirname, token + '.list'))
      )

    if len(self.files) == 0:
      self.files.append(
        FileIterator(pjoin(dirname, 'allposts.list'))
      )

# TODO: support range queries.

def query(c, tokens, max_results=64, merger='AND'):
  assert merger in ['AND', 'OR']
  matches = []
  num_excluded = 0

  tokens = list(set(tokens))

  # TODO: convert word-tokens to lowercase.

  # Process depth tokens
  depthTokens = [t for t in tokens if t[:6] == 'depth:']
  if len(depthTokens) > 1:
    return 'Query contains mutually exclusive depth constraints.'
  for t in depthTokens:
    del tokens[tokens.index(t)]
  # Make sure depths are integers
  for t in depthTokens:
    try:
      int(t[6:])
    except:
      return 'Query contains non-integer depth constraint'
  # Clip at 10, dedup, and add back to tokens
  tokens += list(set([f'depth:{min(int(t[6:]), 20)}' for t in depthTokens]))
  
  lists = ListFetcher(pjoin('index', dirname), tokens)

  merger = Intersection(*lists.files)

  for candidate in merger:
    id_ = int(candidate[8:], 36)
    c.execute(f"SELECT json FROM comments WHERE id={id_}")
    j = json.loads(c.fetchone()[0])
    index_tokens = j['tokens'].split(' ')
    if len([t for t in tokens if t in index_tokens]) != len(tokens):
      num_excluded += 1
      continue
    if len(depthTokens) > 0:
      if j['depth'] != int(depthTokens[0][6:]):
        num_excluded += 1
        continue
    matches.append(j)
    if len(matches) >= max_results:
      break
  return {
    "comments": matches,
    "num_excluded": num_excluded
  }

if __name__ == '__main__':
  conn = sqlite3.connect('comments.db')
  c = conn.cursor()
  a = query(c, ['author:ralf_', 'humans'], 3)