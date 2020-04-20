from utils import *
import matplotlib.pyplot as plt
import numpy as np

parser = MyHTMLParser()

argparser = argparse.ArgumentParser()
argparser.add_argument("--kNumTokens", type=int, default=8192)
args = argparser.parse_args()

# Sample from first 10k posts to find word frequencies.
F = {}
it = -1
for thread in threads():
  if it > 10000:
      break
  comments = thread['comments']
  for comment in comments:
    if 'body_html' not in comment:
      continue
    it += 1
    if it > 10000:
      break
    id_ = int(comment['id'], 36)
    parser.reset()
    parser.feed(comment['body_html'])
    parser.close()
    tokens = get_tokens(parser.text)
    for token in tokens:
      F[token] = F.get(token, 0) + 1
bad = []
# Write the most common words to bad.json
for k in F:
  if F[k] > 2000:
    bad.append(k)

with open(pjoin('bad.json'), 'w+') as f:
  json.dump(bad, f)
