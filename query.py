import json, os, sys, time
from datetime import datetime
from utils import *
pjoin = os.path.join

from union import FileINode, AndINode, OrINode
from expression_parser import str2tree, tokenize

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

  # Lower-case word tokens
  words = [w if ':' in w else w.lower() for w in words]

  tokens = [h(t) % kNumTokens for t in words]
  tokens = [pad(hex(t)[2:], n=5, c='0') for t in tokens]
  tokens = list(tokens)

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
        FileINode(pjoin(dirname, token + '.list'))
      )

    if len(self.files) == 0:
      self.files.append(
        FileINode(pjoin(dirname, 'allposts.list'))
      )

def query_to_tree(query_text):
  tokens = tokenize(query_text)

  # tokens = tokenize(query_text)
  tokens = [(t if t.lower() != 'or' else '+') for t in tokens]

  # Clip depth/score tokens.
  for i, t in enumerate(tokens):
    if t[:6] == 'depth:':
      tokens[i] = f'depth:{min(int(t[6:]), 20)}'
    elif t[:6] == 'score:':
      tokens[i] = f'score:{max(min(int(t[6:]), 85), -18)}'

  return tokens, str2tree(tokens)

def expressiontree_to_uniontree(tree):
  if tree.op not in '+*':
    token = _words2tokens([tree.op])[0]
    return FileINode(pjoin('index', dirname, token + '.list'))

  children = [expressiontree_to_uniontree(c) for c in tree.children]
  if tree.op == '+':
    return OrINode(*children)
  else:
    return AndINode(*children)

def query(c, query_text, max_results=64):
  if re.findall(r"[^0-9a-zA-Z_\-: \.\+\(\)]+", query_text):
    return f'"{query_text}" contains invalid characters'

  tokens, expression_tree = query_to_tree(query_text)
  union_tree = expressiontree_to_uniontree(expression_tree)

  print(expression_tree)
  print(union_tree.name())
  print(tokens)

  # lists = ListFetcher(pjoin('index', dirname), tokens)

  # merger = Intersection(*lists.files)

  # for candidate in merger:
  matches = []
  num_excluded = 0
  for candidate in union_tree:
    id_ = int(candidate[8:], 36)
    c.execute(f"SELECT json FROM comments WHERE id={id_}")
    j = json.loads(c.fetchone()[0])

    index_tokens = {}
    for t in j['tokens'].split(' '):
      index_tokens[t] = 1

    if expression_tree.eval(index_tokens) == 0:
      num_excluded += 1
      continue

    # TODO: depth/score tokens should be unclipped here.
    matches.append(j)
    if len(matches) >= max_results:
      break

  for m in matches:
    m['body_html'] = m['tokens']

  return {
    "comments": matches,
    "num_excluded": num_excluded,
    'tokens': tokens
  }

if __name__ == '__main__':
  conn = sqlite3.connect('comments.db')
  c = conn.cursor()
  a = query(c, ['author:ralf_', 'humans'], 3)