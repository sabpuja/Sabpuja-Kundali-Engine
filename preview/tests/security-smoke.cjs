// Private-network-only synthetic QA for the preview gateway. No real client data.
const assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.QA_ORIGIN||'http://sabpuja-kundali-preview:8080';
// The exact Origin listed in the gateway's allowed-origins map for this run.
const allowedOrigin=process.env.QA_ALLOWED_ORIGIN||new URL(base).origin;
const username=process.env.QA_USER||'qa';const pass=process.env.QA_PASSWORD;if(!pass)throw Error('QA_PASSWORD required');
const auth='Basic '+Buffer.from(username+':'+pass).toString('base64');
(async()=>{
  const result={checks:[],status:'FAIL'};
  const check=(name,ok,detail)=>{result.checks.push({name,passed:ok,detail});console.log(ok?'PASS '+name:'FAIL '+name,detail||'');assert.ok(ok,name)};
  const fetchCode=(url,opts={})=>fetch(url,{signal:AbortSignal.timeout(10000),...opts}).then(r=>r.status);
  check('missing auth 401',await fetchCode(base+'/api/places')===401);
  check('wrong auth 401',await fetchCode(base+'/api/places',{headers:{Authorization:'Basic '+Buffer.from(username+':incorrect').toString('base64')}})===401);
  const good=await fetch(base+'/api/places',{headers:{Authorization:auth}});
  check('correct auth 200',good.status===200);
  check('privacy response headers',good.headers.get('cache-control')?.includes('no-store')&&good.headers.get('x-robots-tag')?.includes('noindex'));
  const places=(await good.json()).places;
  check('ten India locations',places.length===10&&places.every(p=>p.country==='India'));
  check('bad Origin 403',await fetchCode(base+'/api/chart',{method:'POST',headers:{Authorization:auth,Origin:'https://another.example', 'Content-Type':'application/json'},body:'{}'})===403);
  check('oversize 413',await fetchCode(base+'/api/chart',{method:'POST',headers:{Authorization:auth,Origin:allowedOrigin,'Content-Type':'application/json'},body:'x'.repeat(5000)})===413);
  const body=JSON.stringify({place_id:'in-new-delhi',birth_date:'1990-05-15',birth_time:'10:30'});
  const headers={Authorization:auth,Origin:allowedOrigin,'Content-Type':'application/json'};
  const burst=await Promise.all(Array.from({length:18},()=>fetchCode(base+'/api/chart',{method:'POST',headers,body}).catch(()=>0)));
  check('chart rate limit 429',burst.includes(429),JSON.stringify(burst.reduce((a,v)=>(a[v]=(a[v]||0)+1,a),{})));
  // Forged client-address headers from an untrusted caller must not open a new throttling bucket.
  await new Promise(r=>setTimeout(r,4000));
  const forged=await Promise.all(Array.from({length:18},(_,i)=>fetchCode(base+'/api/chart',{method:'POST',headers:{...headers,'X-Forwarded-For':'203.0.113.'+(i+1),'X-Real-IP':'198.51.100.'+(i+1)},body}).catch(()=>0)));
  check('forged X-Forwarded-For still 429',forged.includes(429),JSON.stringify(forged.reduce((a,v)=>(a[v]=(a[v]||0)+1,a),{})));
  const flood=await Promise.all(Array.from({length:80},()=>fetchCode(base+'/api/places',{headers:{Authorization:auth}}).catch(()=>0)));
  check('general rate limit 429',flood.includes(429),JSON.stringify(flood.reduce((a,v)=>(a[v]=(a[v]||0)+1,a),{})));
  result.status='PASS';
  const out=process.env.QA_RESULTS||'/qa/browser-results';
  fs.mkdirSync(out,{recursive:true});
  fs.writeFileSync(out+'/security-result.json',JSON.stringify(result,null,2)+'\n');
  console.log('GATEWAY_SECURITY_PASS '+result.checks.length);
})().catch(e=>{console.error(e.stack);process.exitCode=1});
