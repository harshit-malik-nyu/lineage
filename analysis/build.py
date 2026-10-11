"""Rebuild a typed SQLite evidence mart and query outputs using only committed inputs."""
from pathlib import Path
import csv, hashlib, json, sqlite3, sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/output'
sources={}
def record(path): sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
def read_json(path):
 record(path)
 return json.loads(path.read_text())
def read_csv(path):
 record(path)
 with path.open(newline='') as f:return list(csv.DictReader(f))

rows=[(r['id'],r['root'],r['downloads'],r['depth'],int(r['root_resolved']),int(r['cycle'])) for r in read_json(ROOT/'evidence/derivatives.json')]

OUT.mkdir(exist_ok=True)
db=sqlite3.connect(':memory:')
db.execute('CREATE TABLE observations (model TEXT PRIMARY KEY,root TEXT,downloads INTEGER CHECK(downloads>=0),depth INTEGER CHECK(depth>=0),root_resolved INTEGER CHECK(root_resolved IN(0,1)),cycle INTEGER CHECK(cycle IN(0,1)))')
db.executemany('INSERT INTO observations (model,root,downloads,depth,root_resolved,cycle) VALUES (?,?,?,?,?,?)',rows)
assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert db.execute('SELECT COUNT(*) FROM observations').fetchone()[0]==len(rows)>0
queries=(ROOT/'analysis/questions.sql').read_text().split(';')
outputs=[]
for i,query in enumerate(queries,1):
 if not query.strip():continue
 cursor=db.execute(query)
 path=OUT/f'query_{i}.csv'
 with path.open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow([d[0] for d in cursor.description]);writer.writerows(cursor.fetchall())
 outputs.append(path.name)
manifest={'project':'lineage','rows':len(rows),'scope':'Self-declared Hub metadata snapshot; downloads are not unique users and selected models are not a population sample.','input_sha256':sources,'query_sha256':hashlib.sha256((ROOT/'analysis/questions.sql').read_bytes()).hexdigest(),'outputs':{n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in outputs},'quality_checks':['SQL type and domain constraints','row-count reconciliation','SQLite integrity'],'external_services_required':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps({'project':'lineage','rows':len(rows),'outputs':outputs}))
