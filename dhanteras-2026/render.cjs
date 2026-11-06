// Renders poster.html to PNGs: node render.cjs
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const formats = [['post', 1350], ['status', 1920]];
  for (const [f, h] of formats) {
    const page = await browser.newPage({ viewport: { width: 1080, height: h }, deviceScaleFactor: 1 });
    await page.goto('file://' + path.join(__dirname, 'poster.html') + '?f=' + f);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    const out = path.join(__dirname, `dhanteras_${f}_1080x${h}.png`);
    await page.screenshot({ path: out });
    console.log('wrote', out);
  }
  await browser.close();
})();
