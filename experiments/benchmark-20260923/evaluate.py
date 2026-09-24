import json,hashlib
from pathlib import Path
root=Path('experiments/benchmark-20260923');r=root/'results'
freeze=json.loads((root/'frozen.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in freeze['files'].items())
ref=json.loads((root/'reference-holdout.json').read_text(encoding='utf-8'))
metrics={}
for method in ['direct','lexical','hybrid']:
 m={'expected_items':9,'output_items':0,'correct_quantities':0,'correct_auto_sku':0,'wrong_auto_sku':0,'review_items':0,'candidate_recall':0,'correct_units_on_auto_sku':0,'required_comments_preserved':0,'misplaced_comments':0,'llm_prompt_tokens':0,'llm_completion_tokens':0}
 for name in ['test1','test2']:
  result=json.loads((r/f'v2-{name}-{method}-result.json').read_text(encoding='utf-8'))['items'];m['output_items']+=len(result)
  for got,want in zip(result,ref[name]):
   m['correct_quantities']+=got['quantity']==want['quantity']
   auto=not got['needs_review'] and bool(got['nomenclature_id'])
   correct=got['nomenclature_id'] in want['allowed_ids'] and not want['ambiguous']
   m['correct_auto_sku']+=auto and correct
   m['wrong_auto_sku']+=auto and not correct
   m['review_items']+=bool(got['needs_review'])
   m['candidate_recall']+=bool(set(got['candidate_ids']) & set(want['allowed_ids']))
   m['correct_units_on_auto_sku']+=auto and correct and got['unit']==want['unit']
   comment=got.get('notes') or ''
   if want.get('required_comment'):m['required_comments_preserved']+=want['required_comment'] in comment
   elif comment:m['misplaced_comments']+=1
  paths=[r/f'v2-{name}-direct-raw.json'] if method=='direct' else [r/f'v2-{name}-extract.json',*r.glob(f'v2-{name}-{method}-match-*.json')]
  for p in paths:
   usage=json.loads(p.read_text(encoding='utf-8')).get('usage',{})
   m['llm_prompt_tokens']+=usage.get('prompt_tokens',0);m['llm_completion_tokens']+=usage.get('completion_tokens',0)
 metrics[method]=m
(root/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(metrics,ensure_ascii=False,indent=2))
