// Renders output/coffee_table_3d.stl to images/*.png with three.js in headless
// Chromium. Usage: cd render && npm install && node render.cjs
// Needs Playwright with Chromium available (npm i -g playwright).
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.stl': 'model/stl' };
const server = http.createServer((req, res) => {
  const file = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(root) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});

const views = [
  ['three_quarter', 35, 22, 2500],
  ['front', 90, 8, 2400],
  ['side', 0, 8, 2400],
  ['low_angle', -140, 12, 2400],
];

server.listen(0, async () => {
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  page.on('pageerror', e => console.error(e.message));
  for (const [name, az, el, d] of views) {
    await page.goto(`http://localhost:${port}/render/index.html?az=${az}&el=${el}&d=${d}`);
    await page.waitForFunction(() => document.title === 'done', null, { timeout: 60000 });
    await page.screenshot({ path: path.join(root, 'images', `render_${name}.png`) });
    console.log(`images/render_${name}.png`);
  }
  await browser.close();
  server.close();
});
