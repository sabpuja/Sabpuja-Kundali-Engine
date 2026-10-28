// Synthetic-only Playwright test for private PDF download and stale-result protection.
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const base=process.env.QA_ORIGIN||'http://sabpuja-kundali-preview:8080';
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  try{
    for(const width of [280,375,768,1440]){
      const context=await browser.newContext({
        viewport:{width,height:820},acceptDownloads:true,
        httpCredentials:{username:process.env.QA_USER||'qa-download',password:process.env.QA_PASSWORD||'SYNTHETIC-PDF-QA-ONLY'}
      });
      const page=await context.newPage();
      const errors=[];const external=[];const failed=[];
      page.on('requestfailed',r=>failed.push(r.url()+' '+r.failure()?.errorText));
      page.on('pageerror',e=>errors.push(e.message));
      page.on('request',r=>{if(!r.url().startsWith(base+'/')&&!r.url().startsWith('blob:'))external.push(r.url())});
      // The browser sends its real Origin (also on WOFF2 font fetches): QA_ORIGIN's origin must be
      // listed in the gateway's allowed-origins map. Chromium ignores Origin rewrites in page.route.
      const nav=await page.goto(base+'/',{waitUntil:'networkidle'});
      assert.equal(nav.status(),200);
      await page.evaluate(()=>document.fonts.ready);
      assert.equal(await page.evaluate(()=>document.fonts.check('400 12px Inter')&&document.fonts.check('600 12px Poppins')),true);
      await page.waitForFunction(()=>document.querySelectorAll('#place option').length===11);
      assert.equal(await page.locator('#download-pdf').isDisabled(),true);
      await page.locator('#place').selectOption('in-new-delhi');
      await page.locator('#birth-date').fill('1990-05-15');
      await page.locator('#birth-time').fill('10:30:00');
      await page.locator('#submit').click();
      await page.locator('#result').waitFor({state:'visible',timeout:15000});
      assert.equal(await page.locator('#download-pdf').isEnabled(),true);
      const [download]=await Promise.all([
        page.waitForEvent('download',{timeout:20000}),
        page.locator('#download-pdf').click()
      ]);
      assert.equal(download.suggestedFilename(),'Sabpuja-Janma-Kundali.pdf');
      const blob=fs.readFileSync(await download.path());
      assert.equal(blob.slice(0,5).toString(),'%PDF-');
      assert.ok(blob.length>10000&&blob.length<1048576,blob.length);
      await page.locator('#birth-date').fill('1990-05-16');
      assert.equal(await page.locator('#download-pdf').isDisabled(),true);
      assert.equal(await page.locator('#result').isHidden(),true);
      // Regression: a PDF request aborted by an edit must not leave the button saying "Preparing PDF...".
      await new Promise(resolve=>setTimeout(resolve,1200));
      await page.locator('#submit').click();
      await page.locator('#result').waitFor({state:'visible',timeout:15000});
      await page.route('**/api/report',async route=>{await new Promise(r=>setTimeout(r,2500));route.continue().catch(()=>{});});
      let lateDownload=false;
      page.once('download',()=>{lateDownload=true;});
      await page.locator('#download-pdf').click();
      await page.waitForFunction(()=>document.getElementById('download-pdf').textContent==='Preparing PDF...');
      await page.locator('#birth-date').fill('1990-05-17');
      await new Promise(resolve=>setTimeout(resolve,3200));
      assert.equal(lateDownload,false);
      // The deliberately aborted PDF request is expected; any other failure still fails the run.
      for(let i=failed.length-1;i>=0;i--){if(failed[i].endsWith('/api/report net::ERR_ABORTED'))failed.splice(i,1);}
      await page.unroute('**/api/report');
      await new Promise(resolve=>setTimeout(resolve,1200));
      await page.locator('#submit').click();
      await page.locator('#result').waitFor({state:'visible',timeout:15000});
      assert.equal(await page.locator('#download-pdf').textContent(),'Download Kundali PDF');
      assert.equal(await page.locator('#download-pdf').isEnabled(),true);
      await page.locator('#clear').click();
      assert.equal(await page.locator('#download-pdf').isDisabled(),true);
      const dims=await page.evaluate(()=>[document.documentElement.scrollWidth,document.documentElement.clientWidth]);
      assert.ok(dims[0]<=dims[1]+1,'horizontal overflow');
      assert.deepEqual(errors,[]);
      assert.deepEqual(external,[]);
      assert.deepEqual(failed,[]);
      console.log('PDF_BROWSER_PASS',width,'bytes',blob.length);
      await context.close();
      await new Promise(resolve=>setTimeout(resolve,1600));
    }
  } finally{await browser.close()}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
