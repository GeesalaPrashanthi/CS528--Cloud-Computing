"""Create/import the HW6 schema and verify a lossless normalization round trip."""
import argparse,csv,json,os
from pathlib import Path
from db import connect
FIELDS=['request_id','request_time','country','client_ip','gender','age','income','is_banned','time_of_day','requested_file','http_status']
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--input-csv',type=Path);a=p.parse_args()
name=os.getenv('DB_NAME','cs528_hw6')
if not name.replace('_','').isalnum():raise ValueError('Invalid database name')
c=connect(database=None);c.autocommit(True)
try:
 with c.cursor() as q:
  q.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4')
  q.execute(f'USE `{name}`')
  sql='\n'.join(x for x in Path(__file__).with_name('schema.sql').read_text().splitlines() if not x.lstrip().startswith('--'))
  statements=[s.strip() for s in sql.split(';') if s.strip()]
  if a.apply:
   # Create source before import; normalized inserts follow source checks.
   q.execute(statements[0])
  q.execute('SELECT COUNT(*) FROM requests_source');n=q.fetchone()[0]
  if n==0 and a.input_csv:
   with a.input_csv.open(newline='') as f:rows=list(csv.DictReader(f))
   values=[tuple(None if r[k]=='' else r[k] for k in FIELDS) for r in rows]
   try:
    c.begin()
    for start in range(0,len(values),1000):
     q.executemany('INSERT INTO requests_source ('+','.join(FIELDS)+') VALUES ('+','.join(['%s']*len(FIELDS))+')',values[start:start+1000])
    c.commit()
   except BaseException:c.rollback();raise
   n=len(values)
  if n!=100000:raise ValueError(f'Expected 100000 source requests, found {n}')
  for key,value in [('client_ip','country'),('country','is_banned')]:
   q.execute(f'SELECT COUNT(*) FROM (SELECT {key} FROM requests_source GROUP BY {key} HAVING COUNT(DISTINCT {value})>1) conflicts')
   if q.fetchone()[0]:raise ValueError(f'Functional dependency violated: {key} -> {value}')
  q.execute('SELECT COUNT(*) FROM requests_source WHERE country IS NULL OR client_ip IS NULL')
  if q.fetchone()[0]:raise ValueError('Missing IP/country')
  if a.apply:
   for s in statements[1:]:q.execute(s)
  mismatch=' OR '.join(f'NOT(s.{f} <=> v.{f})' for f in FIELDS)
  q.execute('SELECT COUNT(*) FROM requests_source s LEFT JOIN request_details v USING(request_id) WHERE v.request_id IS NULL OR '+mismatch)
  differences=q.fetchone()[0]
  counts={}
  for table in ['requests_source','countries','clients','requests','request_details']:
   q.execute('SELECT COUNT(*) FROM '+table);counts[table]=q.fetchone()[0]
  if differences or counts['request_details']!=n:raise ValueError('Normalization round trip failed')
  result={'database':name,'counts':counts,'round_trip_differences':differences,'schema_verified':True}
  Path('evidence').mkdir(exist_ok=True)
  Path('evidence/schema_verification.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result,indent=2))
finally:c.close()
