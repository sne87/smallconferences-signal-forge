#!/usr/bin/env python3
"""Public social evidence discovery, not employee surveillance.

Bing's web RSS often ignores social site restrictions and returns profiles,
jobs or unrelated news instead of posts. Run smaller, less restrictive searches
against a rotating mix of known association names and early venue signals.
Keep source URLs and distinguish direct posts from profile/activity pages.
No logins, private groups, personal contact details, or role assumptions.
"""
from __future__ import annotations
import hashlib,json,re,urllib.parse
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data'/'social_watch.json'
PLATFORMS={
 'linkedin':('linkedin.com','linkedin.com/posts/'),
 'facebook':('facebook.com','facebook.com/'),
 'threads':('threads.net','threads.net/'),
 'x':('x.com','x.com/'),
 'reddit':('reddit.com','reddit.com/'),
}
GENERAL = [
 ('conference-site','"association" "conference site selection" "2028"'),
 ('future-city','"2029 conference" "location" "committee"'),
 ('hotel-terms','"association" "conference hotel" "contract"'),
 ('host-venue','"2028" "conference" "host site" "looking"'),
 ('outgoing-chair','"conference chair" "stepping down" association'),
 ('planning-debrief','"annual conference" "feedback" "committee"'),
 ('venue-input','"conference" "where should" "held"'),
 ('association-budget','"conference planning" "venue budget"'),
 ('person-planning','"conference site selection committee" "appointed"'),
 ('hotel-decision','"association" "next conference" "hotel"'),
 ('site-vote','"annual meeting" "site selection" "vote"'),
 ('local-host','"association" "local host committee" "2028"'),
]
# Deep scan: 14 social searches with organization-specific searches using the
# WHOLE organization name. Light scan: 6. No direct employee targeting unless
# a named post itself establishes the relationship in public source text.
def social_searches(now,light,known_names=()):
    cap=6 if light else 14
    day=now.toordinal()
    unique=list(dict.fromkeys(str(n).strip() for n in known_names if len(str(n).strip())>10))
    unique.sort(key=lambda x:x.lower())
    batch=[]
    general_count=3 if light else 6
    for i in range(general_count):
        topic,terms=GENERAL[(day+now.hour+i)%len(GENERAL)]
        platform=['linkedin','facebook','linkedin','reddit','threads','x'][i%6]
        restrict=('site:linkedin.com/posts/' if platform=='linkedin'
                  else 'site:facebook.com/' if platform=='facebook'
                  else 'site:reddit.com/comments/' if platform=='reddit'
                  else 'site:threads.net/' if platform=='threads'
                  else 'site:x.com/' )
        batch.append((f'social-{platform}-general-{topic}',restrict+' '+terms))
    # Follow association board/committee members in public search snippets,
    # but never assume someone is an employee based on an indexed mention.
    if unique:
        for i in range(cap-general_count):
            name=unique[(day*5+now.hour*3+i)%len(unique)]
            platform='linkedin' if i%3!=2 else 'facebook'
            suffix=(' "conference" "planning"' if i%3==0 else
                    ' "annual meeting" "venue"' if i%3==1 else
                    ' "conference" "committee"')
            restrict='site:linkedin.com/posts/' if platform=='linkedin' else 'site:facebook.com/'
            batch.append((f'social-{platform}-org-roles',restrict+' "'+name.replace('"','')+'"'+suffix))
    return batch

def platform_for_url(url):
    try:p=urllib.parse.urlsplit(url);h=(p.hostname or '').lower().removeprefix('www.');path=p.path.lower()
    except ValueError:return ''
    if h=='linkedin.com' and (path.startswith('/posts/') or path.startswith('/feed/update/')):return 'linkedin'
    if h=='facebook.com' and (('/posts/' in path) or '/permalink.php' in path or '/story.php' in path or '/watch/' in path):return 'facebook'
    if h in ('x.com','twitter.com') and '/status/' in path:return 'x'
    if h in ('threads.net','threads.com') and '/post/' in path:return 'threads'
    if h=='reddit.com' and '/comments/' in path:return 'reddit'
    return ''

def public_social_page_for_url(url):
    try:h=(urllib.parse.urlsplit(url).hostname or '').lower().removeprefix('www.')
    except ValueError:return ''
    if h=='linkedin.com' and urllib.parse.urlsplit(url).path.startswith(('/company/','/in/')):return 'linkedin'
    if h in ('facebook.com','threads.net','threads.com','x.com','twitter.com','reddit.com'):return platform_for_url(url) or 'profile'
    return ''

def exact_organizer_mention(article,known_names):
    text=' '.join((str(article.get('title','')),str(article.get('summary',''))))
    for name in sorted(known_names,key=len,reverse=True):
        if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text,re.I):return name
    return ''

def watch_record(article,query_label,known_names,now):
    url=str(article.get('url','')).strip()
    platform=platform_for_url(url)
    if not platform:return None
    title=str(article.get('title','')).strip()
    summary=str(article.get('summary','')).strip()
    if not title or not summary:return None
    if not re.search(r'\b(?:conference|convention|annual meeting|annual conference|site selection|host site|conference committee)\b',title+' '+summary,re.I):return None
    org=exact_organizer_mention(article,known_names)
    # Don't equate a poster with a decision maker. A person may be an attendee,
    # committee volunteer, staffer, or someone merely resharing content.
    evidence=hashlib.sha256(url.split('#')[0].lower().encode()).hexdigest()[:20]
    return {
      'id':evidence,'url':url[:900],'platform':platform,'post_title':title[:260],
      'excerpt':summary[:700],'organizer_mentioned':org,
      'organizer_verified':False,'author_affiliation_verified':False,
      'public_post_date_verified':False,'index_date':article.get('published',''),
      'indexed_by':'public web/news index','query_id':query_label,
      'first_seen':now.date().isoformat(),'last_seen':now.date().isoformat(),
      'review_status':'public_post_requires_original_and_role_review',
      'caution':'Public indexed snippet only. Author affiliation, decision authority, event cycle, venue contracting and buying intent unknown.'}

def combine_records(previous,items,now,max_records=180):
    today=now.date().isoformat()
    merged={x['id']:x for x in previous if isinstance(x,dict) and x.get('id') and x.get('url')}
    for item in items:
        old=merged.get(item['id'],{})
        item['first_seen']=old.get('first_seen',today)
        merged[item['id']]=item
    # A stale indexed post is not automatically a current planning event.
    return sorted(merged.values(),key=lambda a:(a.get('last_seen',''),a.get('index_date','')),reverse=True)[:max_records]

def read_archive(path=DEST):
    try:
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        return d.get('items',[]) if isinstance(d.get('items'),list) else []
    except (OSError,ValueError,TypeError):return []

def save_archive(records,now,attempted,returned,rejected,errors,path=DEST):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    obj={'generated_at':now.isoformat(timespec='seconds'),'source':'public web-indexed social URLs only',
         'social_queries_attempted':attempted,'indexed_social_urls_returned':returned,
         'public_posts_retained':len(records),'rejected_social_index_hits':rejected,
         'errors':errors[:12],
         'notices':['Public posts may be omitted by search-engine indexes. No API login or private group access is used.',
                    'Public post or commenter is not automatically an employee, buyer or event-planning decision maker.',
                    'A committee planning the conference program is different from selecting hotels or hiring a planner.'],
         'items':records}
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return obj
