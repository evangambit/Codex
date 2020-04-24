import mimetypes, re, sqlite3, sys, time
import http.server
import socketserver
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse, parse_qs

import pystache
from query import query

conn = sqlite3.connect('comments.db')
c = conn.cursor()

ext2type = mimetypes.types_map.copy()

class FindAndBoldTermsHTMLParser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.terms = set()

  def reset(self):
    super().reset()
    self.html = ''

  def handle_starttag(self, tag, attrs):
    r = '<' + tag
    for key, value in attrs:
      r += f' {key}="{value}"'
    r += '>'
    self.html += r

  def handle_endtag(self, tag):
    self.html += f'</{tag}>'

  def handle_data(self, data):
    if 'Apple Inc' in data:
      print('====' * 9)
      print(data)
    for term in self.terms:
      data = re.sub(
        re.compile(f"[^\\w\\d]({term})[^\\w\\d]", re.IGNORECASE),
        r" <span class='term'>\1</span> ",
        data,
      )
      data = re.sub(
        re.compile(f"^({term})[^\\w\\d]", re.IGNORECASE),
        r"<span class='term'>\1</span> ",
        data,
      )
    self.html += data

boulder = FindAndBoldTermsHTMLParser()

class MyServer(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
    if self.path[:7] == '/search':
      args = parse_qs(urlparse(self.path).query)
      self.search(args)
    else:
      self.servefile()
  
  def servefile(self):
    path = self.path[1:]
    try:
      f = open(path, 'rb')
    except IOError:
      self.send_error(404, 'File not found')
      return
    self.send_response(200)
    # self.send_header('Content-type', 'image/png')
    self.send_header('Content-type', ext2type['.' + self.path.split('.')[-1]])
    self.end_headers()
    self.wfile.write(f.read())
    f.close()

  def search(self, args):
    start_time = time.time()
    print(f'search {args}')
    query_text = ' ' + unquote(args.get('query', [''])[0])

    kMaxResults = 100
    query_result = query(c, query_text, max_results = kMaxResults+1)
    if query_result is str:
      self.send_error(500, query_result)
      return

    tokens = query_result['tokens']

    boulder.terms = set([t for t in tokens if (':' not in t) and (t not in '()+')])
    print(boulder.terms)
    for i in range(len(query_result['comments'])):
      comment = query_result['comments'][i]
      comment['subreddit'] = 'slatestarcodex' if 'slatestarcodex' in comment['permalink'] else 'TheMotte'
      comment['idx'] = i + 1
      boulder.reset()
      boulder.feed(comment['body_html'])
      comment['body_html'] = boulder.html
    with open('template.html', 'r') as f:
      text = f.read()
    dt = time.time() - start_time
    msg = f'Over {kMaxResults} results in %.3f seconds' % dt if len(query_result['comments']) == kMaxResults + 1 else f'{len(query_result["comments"])} results in %.3f seconds' % dt
    result = pystache.render(text, {
      'comments': query_result['comments'],
      'num_results_msg': msg,
      'num_excluded': query_result['num_excluded']
    })
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    self.wfile.write(result.encode())

PORT = int(sys.argv[1])

with socketserver.TCPServer(("", PORT), MyServer) as httpd:
  print(f'serving @ {PORT}')
  httpd.serve_forever()

