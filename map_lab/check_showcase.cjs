/* Browser QA for the standalone artifact. Requires Playwright and a browser. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');

(async()=>{
 const executablePath=process.env.CHROME_PATH||(process.platform==='darwin'?'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome':undefined);
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];const requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().startsWith('http'))requests.push(r.url())});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../map-showcase/index.html')).href);
  await page.locator('.map-item').first().waitFor();
  if(await page.locator('#play').textContent()==='Pause')await page.locator('#play').click();
  assert.equal(await page.locator('#pool-total').textContent(),'30,000');
  let tested=0;
  for(const size of [5,7,9]){
   await page.locator(`[data-size="${size}"]`).click();
   assert.equal(await page.locator('.map-item').count(),30);
   assert.equal(await page.locator('.cell').count(),size*size);
   const ids=await page.locator('.map-item').evaluateAll(nodes=>nodes.map(n=>n.dataset.map));
   for(const id of ids){
    await page.locator(`[data-map="${id}"]`).click();
    const max=await page.locator('#scrub').getAttribute('max');
    assert(Number(max)>=4);
    await page.locator('#next').click();
    assert((await page.locator('#move-index').textContent()).startsWith('1 /'));
    await page.locator('#scrub').fill(max);await page.locator('#scrub').dispatchEvent('input');
    assert(await page.locator('#ending').isVisible());
    const winner=await page.locator('#winner').textContent();
    const end=await page.locator('#ending strong').textContent();
    assert(winner.includes('prisoner')?end.includes('escapes'):end.includes('capture'));
    assert(await page.locator('#next').isDisabled());
    await page.locator('#restart').click();assert(!(await page.locator('#ending').isVisible()));
    tested++;
   }
   await page.locator('#role-filter').selectOption('prisoner');assert.equal(await page.locator('.map-item').count(),15);
   await page.locator('#role-filter').selectOption('warder');assert.equal(await page.locator('.map-item').count(),15);
   await page.locator('#role-filter').selectOption('all');
   await page.locator('#level-filter').selectOption('Hard');assert((await page.locator('.map-item').count())>0);
   await page.locator('#level-filter').selectOption('all');
  }
  await page.locator('#choices').check();assert((await page.locator('.cell.option').count())>0);
  await page.locator('.cell.option').first().click();assert((await page.locator('#move-note').textContent()).startsWith('If warder'));
  await page.locator('#choices').uncheck();
  await page.locator('#scrub').fill(await page.locator('#scrub').getAttribute('max'));await page.locator('#scrub').dispatchEvent('input');
  await page.locator('#play').click();await page.waitForTimeout(2100);
  assert((await page.locator('#move-index').textContent()).startsWith('0 /'));
  await page.locator('#play').click();
  await page.screenshot({path:'/tmp/map-atlas-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'/tmp/map-atlas-mobile.png',fullPage:true});
  await page.locator('#methods summary').click();assert(await page.getByText('Difficulty is an explicit hypothesis').isVisible());
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
  console.log(JSON.stringify({maps_tested:tested,errors,external_requests:requests,checks:['all 90 maps','all sizes','role and difficulty filters','step and scrub','terminal winners','loop reset','move inspection','mobile overflow','self-contained offline HTML']}));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
