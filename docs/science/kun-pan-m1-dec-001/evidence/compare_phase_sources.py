import json,sys
fx=json.load(open(sys.argv[1]))
def load(p):
    d={}
    for l in open(p):
        t=l.split()
        if not t: continue
        key=(t[0],' '.join(t[1:3]))
        d[key]=(t[3], t[4] if len(t)>4 else None)
    return d
u=load(sys.argv[2]); n=load(sys.argv[3])
src={'SRC-USNO-PHASES':u,'SRC-NASA-PHASES':n}
mm=0; rows=[]
for c in fx['cases']:
    ph=c['event']['published_phase_name']
    for pv in c['published_values']:
        v=pv['value_utc_minute']; md=v[5:10]; hm=v[11:16]
        live=src[pv['source_id']].get((md,ph))
        ok = live is not None and live[0]==hm
        if not ok: mm+=1
        rows.append((c['case_id'],ph,pv['source_id'],hm,live[0] if live else None,live[1] if live else None,'MATCH' if ok else 'MISMATCH', pv.get('source_markers')))
for r in rows: print('\t'.join(str(x) for x in r))
print('values', len(rows), 'mismatches', mm)
print('live usno entries',len(u),'live nasa entries',len(n))
# inter-source diffs from live
d=[(k,u[k][0],n[k][0]) for k in u if u[k][0]!=n[k][0]]
print('live inter-source differences',len(d)); [print(' ',x) for x in d]
