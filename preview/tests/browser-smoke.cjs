const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.QA_ORIGIN||'http://sabpuja-kundali-preview:8080';
const username=process.env.QA_USER||'qa';const password=process.env.QA_PASSWORD; if(!password)throw Error('QA_PASSWORD must be a synthetic testing credential');
const dir=process.env.QA_RESULTS||'/qa/browser-results';fs.mkdirSync(dir,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,args:['--no-sandbox']});let checks=[];
try{for(const width of [280,375,768,1440]){
 const ctx=await browser.newContext({viewport:{width,height:860},httpCredentials:{username,password}});
 const page=await ctx.newPage();let errors=[];let outside=[];
 // The browser sends its real Origin: QA_ORIGIN's origin must be listed in the gateway's
 // allowed-origins map. Chromium ignores Origin rewrites in page.route, so none is attempted.
 page.on('response',async r=>{if(r.url().includes('/api/chart'))console.log('API_CHART',width,r.status(),(await r.text()).slice(0,400));});
 page.on('response',r=>{if(r.url().includes('/api/places'))console.log('PLACES_RESPONSE',width,r.status());});page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(base+'/'))outside.push(r.url())});
 const nav=await page.goto(base+'/',{waitUntil:'networkidle'});
 assert.equal(nav.status(),200);await page.waitForTimeout(1200);console.log('PLACES_UI',width,await page.locator('#place option').allTextContents(),await page.locator('#status').innerText(),JSON.stringify(errors));await page.waitForFunction(()=>document.querySelectorAll('#place option').length===11,{timeout:5000});
 await page.locator('#place').selectOption('in-new-delhi');await page.locator('#birth-date').fill('1990-05-15');
 await page.locator('#birth-time').fill('10:30:00');await page.locator('#submit').click();
 await page.waitForTimeout(1800); console.log('UI_STATE',width,await page.locator('#status').innerText(),await page.locator('#error-card').innerText().catch(()=>''),JSON.stringify(errors));await page.locator('#result').waitFor({state:'visible',timeout:5000});
 for(const name of ['d1','d9']){assert.equal(await page.locator('#'+name+'-table tbody tr').count(),10);
 assert.ok(await page.locator('#'+name+'-chart *').count()>5);}
 const metric=await page.evaluate(()=>[document.documentElement.scrollWidth,document.documentElement.clientWidth]);
 assert.ok(metric[0]<=metric[1]+1,'overflow '+JSON.stringify(metric));assert.deepEqual(errors,[]);assert.deepEqual(outside,[]);
 await page.screenshot({path:dir+'/'+width+'-synthetic.png',fullPage:true,animations:'disabled'});
 await page.locator('#clear').click();assert.equal(await page.locator('#result').isHidden(),true);
 checks.push({width,status:'PASS',metric});console.log('PASS_BROWSER '+width);await ctx.close();
}fs.writeFileSync(dir+'/result.json',JSON.stringify({status:'PASS',checks},null,2));}finally{await browser.close()}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
