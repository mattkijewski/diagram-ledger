// Local gallery smoke check using an existing Playwright installation.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [modules,output]=process.argv.slice(2);
if(!modules||!output)throw new Error('Usage: node scripts/inspect_gallery.mjs NODE_MODULES OUTPUT_DIRECTORY');
const require=createRequire(path.join(path.resolve(modules),'_gallery.cjs'));
const {chromium}=require('playwright');
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1280,height:950}});
 await page.route(/^https?:/,r=>r.abort());
 await page.goto(pathToFileURL(path.resolve('examples/index.html')).href);
 await page.evaluate(()=>document.fonts.ready);
 const loaded=await page.locator('img').evaluateAll(images=>images.every(i=>i.complete&&i.naturalWidth>0));
 if(!loaded)throw new Error('Missing gallery image');
 await page.locator('#svg-before').check();
 if(!await page.locator('.svg-stage .before').isVisible()||await page.locator('.svg-stage .after').isVisible())throw new Error('Before toggle failed');
 await page.locator('#svg-after').check();
 if(!await page.locator('.svg-stage .after').isVisible())throw new Error('After toggle failed');
 await fs.mkdir(output,{recursive:true});
 await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(overflow)throw new Error('Mobile horizontal overflow');
 await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({imagesLoaded:loaded,beforeAfterToggle:true,mobileHorizontalOverflow:overflow},null,2));
 console.log('GALLERY_VERIFIED');
}finally{await browser.close();}
