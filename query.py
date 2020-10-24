from utils import *
from expression_parser import query_to_tree

from urllib.parse import urlparse
import time

kMaxVal = (float('-inf'), 0)
kDefaultLimit = 1000
kDefaultChunkSize = 1000

class Hash64:
  def __init__(self):
    pass
  def __call__(self, x):
    h = hashlib.sha256()
    h.update(x.encode())
    return int(h.hexdigest()[-16:], 16)
hashfn = Hash64()

def intersect(*iters, limit=kDefaultLimit):
  return atleast(*iters, k=len(iters), limit=limit)

def union(*iters, limit=kDefaultLimit):
  return atleast(*iters, k=1, limit=limit)

def atleast(*iters, k=2, limit=kDefaultLimit):
  assert 1 <= k <= len(iters)

  num_returned = 0
  try:
    vals = [next(it) for it in iters]
    while True:
      minval = min(vals)
      if sum([v == minval for v in vals]) >= k:
        yield minval
        num_returned += 1
        if num_returned >= limit:
          break

      for i in range(len(vals)):
        if vals[i] == minval:
          vals[i] = next(iters[i])

  except StopIteration:
    return

def token_iterator(token, chunksize=kDefaultChunkSize, limit=kDefaultLimit):
  if token is None:
    h = 0
  else:
    h = hashfn(token) - (1 << 63)
  r = []
  i = 0
  num_returned = 0
  offset = 0
  while True:
    if i >= len(r):
      i -= len(r)
      offset += len(r)
      r = c.execute(f"""
        SELECT comment_score, comment_id
        FROM tokens
        WHERE token_hash={h}
        ORDER BY comment_score, comment_id
        LIMIT {chunksize}
        OFFSET {offset}""").fetchall()
    if i >= len(r):
      return
    yield r[i]
    num_returned += 1
    if num_returned >= limit:
      yield kMaxVal
      return
    i += 1

def score_iterator(score, chunksize=kDefaultChunkSize, limit=kDefaultLimit, op='>'):
  r = []
  i = 0
  num_returned = 0
  offset = 0
  while True:
    if i >= len(r):
      i -= len(r)
      offset += len(r)
      r = c.execute(f"""
        SELECT comment_score, comment_id
        FROM tokens
        WHERE comment_score{op}{score}
        AND token_hash=0
        ORDER BY comment_score, comment_id
        LIMIT {chunksize}
        OFFSET {offset}""").fetchall()
      print('score', r[:10])
    if i >= len(r):
      yield kMaxVal
      return
    yield r[i]
    num_returned += 1
    if num_returned >= kDefaultLimit:
      return
    i += 1

parser = MyHTMLParser()
conn = sqlite3.connect('new.db')
c = conn.cursor()

def tree_to_iter(tree, limit=kDefaultLimit):
  print(limit, tree)
  if tree.op == '*':
    return intersect(*[tree_to_iter(c, limit=float('inf')) for c in tree.children], limit=limit)
  if tree.op == '+':
    return union(*[tree_to_iter(c, limit=float('inf')) for c in tree.children], limit=limit)
  if tree.op == '>':
    assert tree.children[0].op == '+'
    thresh = int(tree.children[1].op) + 1
    return atleast(*[
        tree_to_iter(c, limit=float('inf')) for c in tree.children[0].children
      ],
      limit=limit,
      k=thresh
    )

  if tree.op[:6] == 'score>':
    return score_iterator(-int(tree.op[6:]), limit=limit, op='<')
  elif tree.op[:6] == 'score<':
    return score_iterator(-int(tree.op[6:]), limit=limit, op='>')
  elif tree.op[:6] == 'score=':
    return score_iterator(-int(tree.op[6:]), limit=limit, op='=')

  return token_iterator(tree.op, limit=limit)

"""

TODO: if one (or more) of the query tokens is very common it can
take a very long time (e.g. 2 seconds!) to execute because an
overwhelming proportion of the common token's documents do not
contain the rare tokens.

A simple solution is to only use rare tokens for merging and use
random access to check the common tokens.


"""

def query(sql_cursor, user_query, max_results=100):
  tokens = user_query.strip().lower().split(' ')
  it = atleast(
    *[token_iterator(t, limit=float('inf')) for t in tokens],
    k=len(tokens),
    limit=max_results
  )

  R = []
  try:
    for i in range(max_results):
      R.append(next(it))
  except StopIteration:
    pass
  if len(R) > 0 and R[-1] == kMaxVal:
    R.pop()

  R = [
    json.loads(c.execute(f"SELECT json FROM comments WHERE comment_id={r[1]}").fetchone()[0]) for r in R
  ]
  for i in range(len(R)):
    T = R[i]["tokens"].split(' ')
    T.sort()
    R[i]["tokens"] = ' '.join(T)
  return {
    "comments": R,
    "tokens": tokens,
    "num_excluded": 0
  }


if __name__ == '__main__':
  conn = sqlite3.connect('new.db')
  c = conn.cursor()
  R = query(c, 'year:2020 author:you-get-an-upvote many')

# graces point year:2020 author:HlynkaCG




