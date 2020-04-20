
"""

Initial comments:

https://api.reddit.com/comments/fc76p9/api/morechildren?api_type=json

https://api.reddit.com/comments/dgqsj2/api/morechildren?api_type=json&id=fjp5v5u

fjp5v5u


Super useful:
https://alpscode.com/blog/how-to-use-reddit-api/

"""

import code, json, math, os, time
from datetime import datetime
import requests
pjoin = os.path.join

"""
0: no printing
1: errors
2: info
"""
VERBOSITY = 2

class Throttler:
  def __init__(self, qps):
    self.waitTime = 1. / qps
    self.lastTime = 0
  def throttle(self):
    time.sleep(max(0, self.waitTime - (time.time() - self.lastTime)))
    self.lastTime = time.time()

class MoreComments:
  def __init__(self, reddit, json, submission):
    assert json['kind'] == 'more'
    self.reddit = reddit
    self.json = json['data']
    self.id = self.json['id']
    self.submission = submission

  def parent_id(self):
    return self.json['parent_id'][3:]

  def fetch(self):
    if len(self.json["children"]) == 0:
      return [], []

    pid = self.parent_id()
    if pid == self.submission.json['id']:
      link_id = 't3_' + pid
    elif pid in self.submission.comments:
      link_id = self.submission.comments[pid].json['link_id']
    else:
      raise Exception('A "MoreComment" should always have an existing parent')

    url = f'https://api.reddit.com/api/morechildren?api_type=json&link_id={link_id}&children={",".join(self.json["children"])}&order={self.submission.order}'
    result = self.reddit.request(url)
    if result is None:
      return [], []
    assert len(result['json']['errors']) == 0

    children = result['json']['data']['things']
    
    comments, mores = [], []
    for child in children:
      assert child['kind'] in ['t1', 'more'], child['kind']
      if child['kind'] == 'more':
        mores.append(MoreComments(self.reddit, child, self.submission))
      elif child['kind'] == 't1':
        comments.append(Comment(child))

    return comments, mores

class Comment:
  def __init__(self, json):
    assert json['kind'] == 't1', json['kind']
    self.json = json['data']
    self.id = self.json['id']

class Submission:
  def __init__(self, reddit, submission_id, order):
    assert order in ['confidence', 'top', 'new', 'controversial', 'old', 'random', 'qa', 'live']
    self.order = order

    # url = f'https://api.reddit.com/comments/{submission_id}/api/comments&api_type=json&limit=100&sort={order}'
    url = f'https://api.reddit.com/comments/{submission_id}.json?limit=500&sort={order}'
    result = reddit.request(url)
    if result is None:
      if VERBOSITY > 0:
        print(f'Error fetching submission {submission_id}')
      return None

    submission, children = result

    assert submission['kind'] == 'Listing', submission['kind']
    assert len(submission['data']['children']) == 1
    submission = submission['data']['children'][0]
    submission['kind'] == 't3'
    self.json = submission['data']
    self.id = self.json['id']

    assert children['kind'] == 'Listing'
    children = children['data']['children']

    # Fetch all comments.
    self.comments = {}
    self.seenit = set()
    self.mores = []
    self._process_list(children)
    while len(self.mores):
      newMores = []
      for more in self.mores:
        newMores += self._more(more)
      self.mores = newMores

  def _process_list(self, listing):
    for c in listing:
      assert c['kind'] in ['t1', 'more']
      if c['kind'] == 'more':
        m = MoreComments(reddit, c, self)
        if m.id not in self.seenit:
          self.seenit.add(m.id)
          self.mores.append(m)
        assert 'replies' not in c['data']
      else:
        if 'replies' in c['data']:
          r = c['data']['replies']
          del c['data']['replies']
        else:
          r = None
        c = Comment(c)
        self.comments[c.id] = c
        if r:
          assert r['kind'] == 'Listing'
          self._process_list(r['data']['children'])

  def _more(self, more):
    newMores = []
    comments, mores = more.fetch()
    for c in comments:
      assert c.id not in self.comments
      assert type(c) is Comment
      self.comments[c.id] = c
    for m in mores:
      if m.id not in self.seenit:
        newMores.append(m)
        self.seenit.add(m.id)
    if VERBOSITY > 1:
      print(len(self.comments), 'comments')
    return newMores


"""
Maintains reddit authentication, responsible for throttling, and
fulfills api requests (trying multiple times if necessary).
"""
class Reddit:
  def __init__(self):
    with open('secret.json', 'r') as f:
      self.secret = json.load(f)
    self.appid = self.secret['appid']
    self.appsecret = self.secret['appsecret']
    self.useragent = self.secret['useragent']
    self.throttler = Throttler(0.45)

    self.expiresAt = 0
    self.authenticate()

  # Refreshes self.auth if necessary.
  def authenticate(self):
    # We add a 1 minute buffer just to be safe.
    if time.time() + 60 < self.expiresAt:
      return
    if VERBOSITY > 0:
      print('authenticating')
    self.throttler.throttle()
    r = requests.post(
      'https://www.reddit.com/api/v1/access_token',
      data = {
        'grant_type': 'password',
        'username': self.secret['username'],
        'password': self.secret['password']
      },
      headers = { 'user-agent': self.useragent },
      auth = requests.auth.HTTPBasicAuth(self.appid, self.appsecret)
    )
    self.auth = r.json()
    self.expiresAt = time.time() + self.auth['expires_in']

  # Get the most recent submissions.  We can fetch a maximum of 100 at
  # a time, so we fetch 100 and use the oldest post for the next fetch's
  # "before" parameter.  We continue fetching until we have at least
  # 'limit' posts, or until the oldest post isn't younger than max_age.
  def new_submissions(self, subreddit, limit=None, max_age=None):
    assert (limit is not None) or (max_age is not None)
    if limit is None:
      limit = float('inf')
    if max_age is None:
      max_age = float('inf')

    assert (type(limit) is int) or (limit == float('inf'))

    R = []
    kMaxPageSize = 100
    kBaseUrl = f'https://api.reddit.com/r/{subreddit}/new?limit={kMaxPageSize}'

    seenit = set()

    # Initial request for last 100 posts.
    response = self.request(kBaseUrl)
    assert response['kind'] == 'Listing'
    submissions = response['data']['children']
    for i, submission in enumerate(submissions):
      assert submission['kind'] == 't3'
      assert submission['data']['id'] not in seenit
      R.append(submission['data'])
      seenit.add(submission['data']['id'])

    # Follow up requests for additional of posts.
    while (len(R) < limit) and (time.time() - R[-1]['created_utc'] < max_age):
      response = self.request(kBaseUrl + f'&after=t3_{R[-1]["id"]}')
      assert response['kind'] == 'Listing'
      submissions = response['data']['children']
      for i, submission in enumerate(submissions):
        assert submission['kind'] == 't3'
        assert submission['data']['id'] not in seenit
        R.append(submission['data'])
        seenit.add(submission['data']['id'])

    # We try to always return exactly the limit.
    if limit < len(R):
      R = R[:limit]
    R = [r for r in R if time.time() - r['created_utc'] < max_age]
    return R
  
  # Makes a request to a reddit API url.
  def request(self, url, max_tries=3, headers=None):
    assert max_tries > 0

    # Refresh authentication if necessary.
    self.authenticate()

    # Create headers.
    if headers is None:
      headers = {}
    if 'Authorization' not in headers:
      headers['Authorization'] = self.auth['access_token']
    if 'User-Agent' not in headers:
      headers['User-Agent'] = self.useragent

    # Make request.
    self.throttler.throttle()
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
      return response.json()

    # IF there was an error, print it out.
    if VERBOSITY > 0:
      print(response)

    # Errors that are forbidden generally can't be satisfied by retrying,
    # so we don't bother.
    if response.status_code == 403:
      return None

    # Recursively retry...
    if max_tries > 1:
      time.sleep(3)
      return self.request(url, max_tries - 1)
    else:
      return response

if __name__ == '__main__':
  reddit = Reddit()

  kSecsPerDay = 60*60*24 # 86_400
  kOutDir = 'comments'

  if not os.path.exists(kOutDir):
    os.mkdir(kOutDir)

  # r/TheMotte is typically very slow per comment on account of its habit
  # of having threads with over 400 comments.
  for subreddit in ['TheMotte', 'slatestarcodex']:
    # Grab all posts within the last time period
    S = reddit.new_submissions(subreddit, max_age=kSecsPerDay*14)

    # Grab all comments for these posts
    for s in S:
      fn = s['id'] + '.json'
      year = str(datetime.utcfromtimestamp(s['created_utc']).year)
      print('https://www.reddit.com' + s['permalink'])

      submission = Submission(reddit, s['id'], order='new')

      # We cannot consistently find all comments when there are more than
      # 400 comments in a submission (some flaw with reddit's API?) but if
      # we request with many different orders we can typically find (almost?)
      # every comment.
      if submission.json['num_comments'] > 400:
        S1 = Submission(reddit, submission.id, order='new')
        S2 = Submission(reddit, submission.id, order='old')
        S3 = Submission(reddit, submission.id, order='top')
        S4 = Submission(reddit, submission.id, order='controversial')
        S5 = Submission(reddit, submission.id, order='random')
        C = {}
        for k in S1.comments:
          C[k] = S1.comments[k].json
        for k in S2.comments:
          C[k] = S2.comments[k].json
        for k in S3.comments:
          C[k] = S3.comments[k].json
        for k in S4.comments:
          C[k] = S4.comments[k].json
        for k in S5.comments:
          C[k] = S5.comments[k].json
        submission.comments = C
      else:
        C = submission.comments
        submission.comments = {}
        for k in C:
          submission.comments[k] = C[k].json

      if not os.path.exists(pjoin(kOutDir, year)):
        os.mkdir(pjoin(kOutDir, year))

      if os.path.exists(pjoin(kOutDir, year, fn)):
       with open(pjoin(kOutDir, year, fn), 'r') as f:
          old = json.load(f)
      else:
        old = {'comments': []}

      for c in old['comments']:
        if c['id'] not in submission.comments:
          submission.comments[c['id']] = c

      print(len(submission.comments), 'out of', submission.json['num_comments'])

      j = submission.json
      j['comments'] = list(submission.comments.values())

      with open(pjoin(kOutDir, year, fn), 'w+') as f:
        json.dump(j, f)

