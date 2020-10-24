import json, sqlite3

conn = sqlite3.connect('new.db')
c = conn.cursor()

c.execute('SELECT json FROM comments')

F = {}

n = 100000
for it in range(n):
  j = json.loads(c.fetchone()[0])
  for token in j['tokens'].split(' '):
    F[token] = F.get(token, 0) + 1

badkeys = []
for token in F:
  F[token] /= n
  if F[token] < 0.01:
    badkeys.append(token)

for key in badkeys:
  del F[key]

A = list(zip(F.values(), F.keys()))
A.sort(key=lambda x:-x[0])

for a in A[:64]:
  print(a)