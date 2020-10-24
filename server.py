from utils import *

import mimetypes, re, sqlite3, sys, time
import http.server
import socketserver
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse, parse_qs

import pystache
from spotquery import query
import spot

import cgi

index = spot.Index('spot-index')

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
    # self.html += cgi.escape(data)
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

    try:
      max_results = int(args["max_results"][0])
    except:
      max_results = 100

    query_result = query(index, query_text, max_results = max_results+1)
    if type(query_result) is str:
      self.send_error(500, query_result)
      return

    for comment in query_result['comments']:
      tokens = comment["tokens"].split(' ')
      tokens = [t for t in tokens if t[:8] == 'pauthor:']
      if len(tokens) > 0:
        comment["pauthor"] = tokens[0][8:]

    tokens = query_result['tokens']

    parser = MyHTMLParser()

    boulder.terms = set([t for t in tokens if (':' not in t) and (t not in '()+')])
    print('tokens' ,boulder.terms)
    for i in range(len(query_result['comments'])):
      comment = query_result['comments'][i]
      comment['subreddit'] = 'slatestarcodex' if 'slatestarcodex' in comment['permalink'] else 'TheMotte'
      comment['idx'] = i + 1
      parser.reset()
      parser.feed(comment["body_html"])

      boulder.reset()
      boulder.feed(parser.alltext)
      comment['body_html'] = boulder.html

    with open('template.html', 'r') as f:
      text = f.read()
    dt = time.time() - start_time
    msg = f'Over {max_results} results in %.3f seconds' % dt if len(query_result['comments']) == max_results + 1 else f'{len(query_result["comments"])} results in %.3f seconds' % dt
    result = pystache.render(text, {
      'comments': query_result['comments'],
      'num_results_msg': msg
    })
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    self.wfile.write(result.encode())

PORT = int(sys.argv[1])

with socketserver.TCPServer(("", PORT), MyServer) as httpd:
  print(f'serving @ {PORT}')
  httpd.serve_forever()

