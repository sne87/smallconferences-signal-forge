#!/usr/bin/env python3
"""One-time search-provider smoke check (bounded public indexed links only)."""
import re, urllib.parse, urllib.request
from html.parser import HTMLParser

q='site:linkedin.com/posts/ "2028" "host city" "conference"'
sources=[
 ('duckduckgo','https://html.duckduckgo.com/html/?q='+urllib.parse.quote(q)),
 ('bing_html','https://www.bing.com/search?q='+urllib.parse.quote(q)+'&count=12'),
 ('google_html','https://www.google.com/search?q='+urllib.parse.quote(q)+'&num=12'),
 ('mojeek','https://www.mojeek.com/search?q='+urllib.parse.quote(q)),
]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   d=dict(attrs)
   if d.get('href'):self.links.append(d['href'])
def clean(url):
 try:
  p=urllib.parse.urlsplit(url)
  q=urllib.parse.parse_qs(p.query)
  if 'uddg' in q:return q['uddg'][0]
  if p.path in ('/url','/url/') and 'q' in q:return q['q'][0]
  return url
 except ValueError:return url
for name,url in sources:
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36','Accept':'text/html,*/*'})
  with urllib.request.urlopen(req,timeout=12) as r:
   body=r.read(800000).decode('utf-8','replace');status=r.status
  html=Links();html.feed(body);links=[clean(x) for x in html.links]
  candidates=[x for x in links if 'linkedin.com/posts/' in x and x.startswith('http')]
  print(name,'http',status,'bytes',len(body),'anchors',len(links),'direct_post_links',len(set(candidates)))
  for x in list(dict.fromkeys(candidates))[:2]:print('  sample',x[:250])
 except Exception as exc:print(name,'error',type(exc).__name__,str(exc)[:240])
