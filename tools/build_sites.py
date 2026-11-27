"""Convert Sherlock data.json -> Inspector Rabbit sites.json and validate each site live.

Usage: python tools/build_sites.py <project_root> <sherlock data.json> <old sites.json> <out.json>

A site is kept only if its known username is detected twice AND three random
usernames are all detected as not found.
"""
import json, sys, os, random, string, concurrent.futures, time
sys.path.insert(0, sys.argv[1])           # project root
from src.modules import username_checker as uc, net
sher = json.load(open(sys.argv[2]))
old = json.load(open(sys.argv[3]))
old_cat = {k.lower(): v.get('category','other') for k,v in (old.get('sites', old)).items() if isinstance(v, dict)}
KW = {
 'development': ['git','code','dev','docker','npm','pypi','stack','hack','leet','replit','codepen','kaggle','hugging','sourceforge','launchpad','gitee','codeberg','codewars','hackerrank','hackerone','bugcrowd','tryhackme'],
 'gaming': ['game','steam','xbox','chess','lichess','twitch','roblox','minecraft','osu','speedrun','itch','epic','nintendo','playstation','fortnite','lol','dota','riot','kick'],
 'music': ['music','sound','spotify','bandcamp','last.fm','lastfm','genius','mixcloud','audio','smule','reverbnation','discogs'],
 'art': ['art','dribbble','behance','deviant','flickr','500px','pinterest','unsplash','vsco','artstation','pixiv','photo'],
 'social': ['reddit','twitter','mastodon','bluesky','facebook','instagram','tiktok','vk','ok.ru','telegram','threads','snapchat','tumblr','linktree','about.me','gravatar','keybase','disqus','quora'],
 'blogging': ['medium','blog','wordpress','substack','hashnode','livejournal','write','dev.to'],
 'video': ['youtube','vimeo','dailymotion','rumble','bitchute','odysee'],
 'professional': ['linkedin','angel','fiverr','upwork','freelancer','producthunt','crunchbase','slideshare'],
 'forum': ['forum','community','discourse','board'],
 'finance': ['coin','crypto','bitcoin','paypal','cash','venmo','patreon','ko-fi','buymeacoffee','tradingview'],
 'shopping': ['ebay','etsy','amazon','shop','store','depop','poshmark'],
}
def cat_for(name, rule):
    n = name.lower()
    if n in old_cat: return old_cat[n]
    hay = (n + ' ' + rule.get('urlMain','')).lower()
    for c, kws in KW.items():
        if any(k in hay for k in kws): return c
    return 'other'
sites = {}
for name, r in sher.items():
    if name.startswith('$') or not isinstance(r, dict): continue
    et = r.get('errorType')
    if isinstance(et, list): et = et[0]
    if et not in ('status_code','message','response_url'): continue
    rule = {'url': r['url'], 'error_type': et, 'category': cat_for(name, r),
            'username_claimed': r.get('username_claimed','')}
    if r.get('urlProbe'): rule['url_probe'] = r['urlProbe']
    if r.get('errorCode') is not None: rule['error_code'] = r['errorCode']
    if r.get('errorMsg') is not None: rule['error_msg'] = r['errorMsg']
    if r.get('regexCheck'): rule['regex_check'] = r['regexCheck']
    if r.get('request_method'): rule['request_method'] = r['request_method']
    if r.get('request_payload'): rule['request_payload'] = r['request_payload']
    if r.get('headers'): rule['headers'] = r['headers']
    if r.get('isNSFW'): rule['nsfw'] = True
    sites[name] = rule
print('candidate sites', len(sites))
http = net.session(retries=1)
def rnd(): return 'zq' + ''.join(random.choices(string.ascii_lowercase+string.digits, k=13))
def validate(item):
    name, rule = item
    claimed = rule.get('username_claimed')
    if not claimed: return name, 'no_claimed', None
    a = uc.check_single_site(name, rule, claimed, 15, http)
    if a.state != 'found': return name, f'claimed->{a.state}:{a.status_code}:{a.error}', None
    for _ in range(3):
        b = uc.check_single_site(name, rule, rnd(), 15, http)
        if b.state not in ('not_found','invalid'): return name, f'random->{b.state}:{b.status_code}:{b.error}', None
    a2 = uc.check_single_site(name, rule, claimed, 15, http)
    if a2.state != 'found': return name, f'claimed(2nd)->{a2.state}:{a2.status_code}', None
    return name, 'ok', a.response_time
ok, bad = {}, {}
with concurrent.futures.ThreadPoolExecutor(32) as ex:
    for name, verdict, rt in ex.map(validate, sites.items()):
        (ok if verdict == 'ok' else bad)[name] = verdict
# second chance for transient failures
retry = {n: sites[n] for n, v in bad.items() if 'error' in v or 'blocked' in v or 'Timeout' in v}
time.sleep(5)
with concurrent.futures.ThreadPoolExecutor(8) as ex:
    for name, verdict, rt in ex.map(validate, retry.items()):
        if verdict == 'ok': ok[name] = verdict; bad.pop(name, None)
        else: bad[name] = verdict
print('validated', len(ok), 'rejected', len(bad))
json.dump(bad, open('rejected.json','w'), indent=1)
out = {'_meta': {
        'source': 'Sherlock Project site database (MIT License, https://github.com/sherlock-project/sherlock)',
        'validated_at': time.strftime('%Y-%m-%d'),
        'note': 'Each site verified live: known username detected as found AND random username detected as not found.',
        'count': len(ok)},
       'sites': {n: sites[n] for n in sorted(ok, key=str.lower)}}
json.dump(out, open(sys.argv[4],'w'), indent=1, ensure_ascii=False)
