import json,sys,time,math,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import requests
from repositories import YandexCloudSettingsRepository
from catalog_matching import CatalogIndex,hybrid_rank,guarded_selection,is_metadata
from order_prompts import EXTRACTION_PROMPT,MATCH_PROMPT,DIRECT_PROMPT
ROOT=Path('/tmp/voice-benchmark'); ROOT.mkdir(exist_ok=True)
SETTINGS=YandexCloudSettingsRepository.get_settings()
CATALOG=json.loads((ROOT/'catalog.json').read_text())
INDEX=CatalogIndex(CATALOG)
HEADERS={'Authorization':f'Api-Key {SETTINGS.api_key}','x-folder-id':SETTINGS.folder_id}

def parse(text):
 text=text.strip()
 if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0]
 return json.loads(text)

def chat(prompt,data,label):
 path=ROOT/('v2-'+label+'.json')
 if path.exists():return json.loads(path.read_text())['output']
 start=time.monotonic()
 r=requests.post('https://ai.api.cloud.yandex.net/v1/chat/completions',headers=HEADERS,json={'model':f'gpt://{SETTINGS.folder_id}/{SETTINGS.yandex_model or "yandexgpt"}','temperature':0,'max_tokens':6000,'messages':[{'role':'system','content':prompt},{'role':'user','content':json.dumps(data,ensure_ascii=False)}]},timeout=240)
 r.raise_for_status(); resp=r.json();choice=resp['choices'][0]
 if choice.get('finish_reason')!='stop':raise ValueError('Incomplete output: '+str(choice.get('finish_reason')))
 output=parse(choice['message']['content'])
 path.write_text(json.dumps({'output':output,'seconds':round(time.monotonic()-start,2),'usage':resp.get('usage'),'model':SETTINGS.yandex_model},ensure_ascii=False,indent=2))
 return output

def embed(text,kind):
 key=hashlib.sha256((kind+text).encode()).hexdigest()
 folder=ROOT/'embeddings';folder.mkdir(exist_ok=True);path=folder/(key+'.json')
 if path.exists():return json.loads(path.read_text())
 for attempt in range(4):
  r=requests.post('https://ai.api.cloud.yandex.net/foundationModels/v1/textEmbedding',headers=HEADERS,json={'modelUri':f'emb://{SETTINGS.folder_id}/text-search-{kind}/latest','text':text},timeout=60)
  if r.status_code==429 or r.status_code>=500:
   time.sleep(2**attempt);continue
  r.raise_for_status(); vector=r.json()['embedding'];path.write_text(json.dumps(vector));return vector
 r.raise_for_status()

def compact(rows):return [{'choice':i+1,'name':p['name'],'unit':p.get('storage_unit')} for i,p in enumerate(rows)]

def run(name,method):
 start=time.monotonic();text=json.loads((ROOT/f'{name}-transcript.json').read_text())['text']
 if method=='direct':
  items=chat(DIRECT_PROMPT,{'transcript':text,'catalog':compact(CATALOG)},name+'-direct-raw')
  output=[guarded_selection(item,CATALOG,item) for item in items if not is_metadata(item)]
 else:
  items=[item for item in chat(EXTRACTION_PROMPT,{'transcript':text},name+'-extract') if not is_metadata(item)]
  vectors=json.loads((ROOT/'document-vectors.json').read_text()) if method=='hybrid' else None
  def match(pair):
   i,item=pair; query=' '.join(str(item.get(k) or '') for k in ['spoken_name','attributes','comments'])
   lexical=INDEX.rank(query,limit=30)
   if vectors:
    q=embed(query,'query');qn=math.sqrt(sum(v*v for v in q))
    scores=[sum(a*b for a,b in zip(q,d))/(qn*math.sqrt(sum(v*v for v in d)) or 1) for d in vectors]
    dense=sorted(range(len(scores)),key=lambda j:scores[j],reverse=True)[:30]
    indexes=hybrid_rank(lexical,dense,limit=8)
   else:indexes=lexical[:8]
   candidates=[CATALOG[j] for j in indexes]
   decision=chat(MATCH_PROMPT,{'item':item,'candidates':compact(candidates)},f'{name}-{method}-match-{i:02}')
   result=guarded_selection(item,candidates,decision)
   return result
  with ThreadPoolExecutor(max_workers=4) as pool:output=list(pool.map(match,enumerate(items)))
 (ROOT/f'v2-{name}-{method}-result.json').write_text(json.dumps({'items':output,'seconds':round(time.monotonic()-start,2)},ensure_ascii=False,indent=2))
 print(json.dumps({'name':name,'method':method,'rows':len(output),'matched':sum(bool(p['nomenclature_id']) for p in output),'review':sum(p['needs_review'] for p in output)},ensure_ascii=False),flush=True)

if __name__=='__main__':
 if sys.argv[1]=='index':
  with ThreadPoolExecutor(max_workers=4) as pool: vectors=list(pool.map(lambda p:embed(p['name'],'doc'),CATALOG))
  (ROOT/'document-vectors.json').write_text(json.dumps(vectors));print('Embedded',len(vectors))
 else:run(sys.argv[1],sys.argv[2])
