#!/usr/bin/env python3
"""TIKI trailer catalogue importer; independent of any private credentials."""
import os,re,json,time,html,hashlib,datetime,sys
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup

BASE='https://tiki.ee'
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT,'data','catalog.json')
S=requests.Session();S.headers.update({'User-Agent':'AnhaengerDirektOfficialDealer/1.0 (catalog synchronization; contact via site)','Accept-Language':'et,en;q=0.8'})
CATS={'kastihaagised':'Kastenanhänger','paadihaagised':'Bootsanhänger','rannahaagised':'Strandanhänger','jetihaagised':'Jetski-Anhänger','autoveohaagised':'Autotransporter','sihtotstarbelised-haagised':'Spezialanhänger','generaatorihaagised':'Generatoranhänger','mootorsaanihaagised':'Schneemobilanhänger','furgoonhaagised':'Kofferanhänger','platvormhaagised':'Plattformanhänger','soojakhaagised':'Bauwagen'}
TERMS={'Kastihaagis':'Kastenanhänger','Paadihaagis':'Bootsanhänger','Rannahaagis':'Strandanhänger','Jetihaagis':'Jetski-Anhänger','Autoveohaagis':'Autotransporter','Väiketraktori haagis':'Maschinentransporter','Platvormhaagis':'Plattformanhänger','Furgoonhaagis':'Kofferanhänger','Soojakhaagis':'Bauwagen','Mootorsaanihaagis':'Schneemobilanhänger','Generaatorihaagis':'Generatoranhänger','Kaablihaagis':'Kabeltrommelanhänger','Reklaamhaagis':'Werbeanhänger','plastkaanega':'mit Kunststoffdeckel','Black Edition':'Black Edition','Kõrge poort':'Hohe Bordwand'}
FIELDS={'Kasti laius (m)':'Kastenbreite (m)','Kasti pikkus (m)':'Kastenlänge (m)','Täismass (kg)':'Zulässiges Gesamtgewicht (kg)','Tühimass (kg)':'Leergewicht (kg)','Kandevõime (kg)':'Nutzlast (kg)','Poordikõrgus (m)':'Bordwandhöhe (m)','Haagise pikkus (m)':'Gesamtlänge (m)','Haagise laius (m)':'Gesamtbreite (m)','Pidurid':'Bremse','Raam':'Rahmen','Rehvid':'Reifen','Sild':'Achse','Max paadi pikkus (m)':'Max. Bootslänge (m)'}

def get(url):
 for n in range(3):
  try:
   r=S.get(url,timeout=28);r.raise_for_status(); return r.text
  except requests.RequestException as e:
   print('retry',url,str(e)[:90],file=sys.stderr);time.sleep(2*(n+1))
 return ''
def clean(s):return re.sub(r'\s+',' ',html.unescape(str(s or ''))).strip()
def select_src(img):
 for k in ('data-large_image','data-src','data-lazy-src','src'):
  v=img.get(k,'');
  if v and not v.startswith('data:'):return urljoin(BASE,v)
 return ''
def extract_links(soup):
 links=set()
 for a in soup.select('a[href]'):
  u=urljoin(BASE,a['href']).split('#')[0].split('?')[0]
  if urlparse(u).hostname in ('tiki.ee','www.tiki.ee') and re.search(r'/product/[^/]+/?$',u):links.add(u.rstrip('/')+'/')
 return links

def discovery():
 links=set()
 # First prefer manufacturer sitemap, which avoids missing paginated products.
 for mapurl in [BASE+'/product-sitemap.xml',BASE+'/wp-sitemap-posts-product-1.xml',BASE+'/sitemap_index.xml']:
  raw=get(mapurl)
  if not raw:continue
  soup=BeautifulSoup(raw,'xml')
  for loc in soup.find_all('loc'):
   u=clean(loc.text)
   if re.search(r'/product/[^/]+/?$',u): links.add(u)
   elif 'product-sitemap' in u or 'wp-sitemap-posts-product' in u:
    raw2=get(u)
    if raw2:
     for loc2 in BeautifulSoup(raw2,'xml').find_all('loc'):
      v=clean(loc2.text)
      if '/product/' in v:links.add(v)
  if len(links)>50:break
 # Listing pages supplement sitemap and catch recent items.
 for slug in CATS:
  url=f'{BASE}/tootekategooria/haagised/{slug}/'
  raw=get(url)
  if not raw:continue
  page=BeautifulSoup(raw,'html.parser')
  links.update(extract_links(page))
  count=0
  while count<20:
   nxt=page.select_one('a.next.page-numbers, a[rel="next"]')
   if not nxt:break
   u=urljoin(BASE,nxt.get('href',''))
   if not u.startswith(BASE):break
   raw=get(u)
   if not raw:break
   page=BeautifulSoup(raw,'html.parser');links.update(extract_links(page));count+=1
  time.sleep(.2)
 return sorted(links)

def translate_title(title):
 result=title
 for et,de in sorted(TERMS.items(),key=lambda x:-len(x[0])):result=result.replace(et,de)
 return result

def translate_text(text,key,cache):
 text=clean(text)
 if not text:return ''
 if not key:return '' # NEVER pass untranslated Estonian as German.
 h=hashlib.sha256(text.encode()).hexdigest()
 if h in cache:return cache[h]
 try:
  r=requests.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':'Bearer '+key},json={'model':os.getenv('OPENAI_MODEL','gpt-4o-mini'),'temperature':0,'messages':[{'role':'system','content':'Translate the following Estonian trailer product description into precise natural German. Preserve all dimensions, numbers, model names, features and caveats. Return plain text only. Do not invent technical data.'},{'role':'user','content':text[:12000]}]},timeout=60)
  r.raise_for_status();result=clean(r.json()['choices'][0]['message']['content']);cache[h]=result;return result
 except Exception as e:print('Translation failed',str(e)[:100],file=sys.stderr);return ''

def price_from(text):
 x=re.search(r'ilma\s*KM-ta\s*([\d.,\s]+)\s*€',text,re.I)
 if not x:return None
 s=x.group(1).replace(' ','').replace('\xa0','')
 if ',' in s and '.' in s:s=s.replace('.','').replace(',','.')
 elif ',' in s:s=s.replace(',','.')
 try:return round(float(s),2)
 except:return None

def product(url,key,cache):
 raw=get(url)
 if not raw:return None
 soup=BeautifulSoup(raw,'html.parser')
 title_node=soup.select_one('h1.product_title,h1.entry-title,h1')
 title=clean(title_node.get_text(' ',strip=True)) if title_node else ''
 if not title:return None
 main=soup.select_one('main,article,.product,.site-main') or soup
 text=clean(main.get_text(' ',strip=True))
 net=price_from(text)
 if net is None:
  # Avoid guessing gross-vs-net. Skip price-unverifiable products.
  print('MISSING NET PRICE',url,file=sys.stderr);return None
 sku=''
 sn=main.select_one('.sku');sku=clean(sn.get_text(' ',strip=True)) if sn else ''
 if not sku:
  m=re.search(r'Tootekood:\s*([A-Z0-9-]+)',text)
  if m:sku=m.group(1)
 category='Sonstige Anhänger';rawcat=''
 for a in soup.select('nav.woocommerce-breadcrumb a, .posted_in a, .product_meta a'):
  href=a.get('href','')
  for slug,de in CATS.items():
   if slug in href:category=de;rawcat=slug;break
  if rawcat:break
 if not rawcat:
  for slug,de in CATS.items():
   if slug in raw:category=de;rawcat=slug;break
 images=[]
 for el in soup.select('.woocommerce-product-gallery img,.woocommerce-product-gallery a[href], .product-thumbnails img, .product-gallery img'):
  u=urljoin(BASE,el.get('href','')) if el.name=='a' else select_src(el)
  if not u or not re.search(r'\.(?:jpg|jpeg|png|webp)(?:\?|$)',u,re.I):continue
  if '/wp-content/uploads/' in u:
   u=re.sub(r'-\d+x\d+(?=\.(?:jpg|jpeg|png|webp))','',u,flags=re.I)
  if u not in images:images.append(u)
 if not images:
  for el in soup.select('img[src*="/uploads/"]'):
   u=select_src(el)
   if u and u not in images:images.append(u)
 docs=[]
 for a in main.select('a[href]'):
  u=urljoin(BASE,a.get('href',''))
  if re.search(r'\.(pdf|dwg)(?:\?|$)',u,re.I) and u not in docs:docs.append(u)
 specs={}
 for row in main.select('table tr'):
  cells=row.find_all(['th','td'])
  if len(cells)==2:
   k=clean(cells[0].get_text(' ',strip=True)).rstrip(':');v=clean(cells[1].get_text(' ',strip=True))
   if k in FIELDS and v:specs[FIELDS[k]]=v
 # TIKI uses many technical fields as a sequence of labels and values.
 for et,de in FIELDS.items():
  if de in specs:continue
  expr=re.compile(re.escape(et)+r'\s*:?\s*([^\s]+(?:\s*[/x×]\s*[^\s]+)?)',re.I)
  m=expr.search(text)
  if m and len(m.group(1))<65:specs[de]=m.group(1)
 desc_el=main.select_one('#tab-description, .woocommerce-Tabs-panel--description, .product-description')
 description=clean(desc_el.get_text(' ',strip=True)) if desc_el else ''
 if not description:
  h=main.find(lambda tag:tag.name in ('h2','h3') and clean(tag.get_text())=='Kirjeldus')
  if h:
   p=h.find_next(['p','div'])
   if p:description=clean(p.get_text(' ',strip=True))
 german_desc=translate_text(description,key,cache) if description else ''
 # The default public price is always sourced from explicitly marked net amount.
 newnet=round(net+1000,2);gross=round(newnet*1.19+1e-7,2)
 return {'id':sku or url.rstrip('/').split('/')[-1],'sku':sku,'title':translate_title(title),'original_title':title,'category':category,'source_url':url,'net_estonia':net,'net_germany':newnet,'gross_germany':gross,'images':images,'documents':docs,'specifications':specs,'description_de':german_desc,'translation_status':'complete' if german_desc else 'description_pending','last_checked':datetime.datetime.now(datetime.timezone.utc).isoformat()}

def run():
 key=os.environ.get('OPENAI_API_KEY','')
 cachefile=os.path.join(ROOT,'data','translations.json')
 try:cache=json.load(open(cachefile))
 except:cache={}
 urls=discovery();print('Discovered:',len(urls),flush=True)
 if not urls:raise RuntimeError('No TIKI product URLs found; refusing to overwrite catalogue')
 items=[]
 for i,url in enumerate(urls,1):
  obj=product(url,key,cache)
  if obj:items.append(obj)
  if i%20==0:print('Read:',i,'valid:',len(items),flush=True)
  time.sleep(.15)
 if len(items)<10:raise RuntimeError('Fewer than 10 valid products; refusing to replace catalogue')
 os.makedirs(os.path.dirname(OUT),exist_ok=True)
 existing=[]
 try:existing=json.load(open(OUT))['products']
 except:pass
 # Guard against mass deletions caused by temporary source site issues.
 if existing and len(items)<len(existing)*.65:raise RuntimeError('Abnormally large product drop; refusing overwrite')
 result={'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':BASE,'markup_eur':1000,'vat':0.19,'count':len(items),'products':sorted(items,key=lambda o:o['title'])}
 with open(OUT,'w') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 if key:
  with open(cachefile,'w') as f:json.dump(cache,f,ensure_ascii=False,indent=2)
 print('DONE:',len(items),'products')
if __name__=='__main__':run()
