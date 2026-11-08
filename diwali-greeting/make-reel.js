// Records reel.html frame-by-frame into a WhatsApp-ready MP4 (1080x1920, 30 fps, H.264 + AAC)
// and exports a still greeting card.
//
// usage: node make-reel.js [outDir] [--from "English names"] [--fromhi "हिंदी नाम"] [--family "X Family"]
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : null; };
const params = new URLSearchParams({ capture: '1' });
for (const k of ['from', 'fromhi', 'family']) { const v = opt('--' + k); if (v) params.set(k, v); }
const out = path.resolve(args[0] || path.join(__dirname, 'output'));
fs.mkdirSync(out, { recursive: true });
const FPS = 30;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', (e) => console.error('page error:', e.message));
  await page.goto('file://' + path.join(__dirname, 'reel.html') + '?' + params);
  await page.evaluate(() => window.fontsReady);
  const { dur, hero, fireworks } = await page.evaluate(() => ({ dur: window.DUR, hero: window.HERO, fireworks: window.FIREWORKS }));

  // soundtrack synced to the firework schedule
  const fwJson = path.join(out, 'fireworks.json');
  const wav = path.join(out, 'soundtrack.wav');
  fs.writeFileSync(fwJson, JSON.stringify(fireworks));
  execFileSync('python3', [path.join(__dirname, 'soundtrack.py'), fwJson, wav, String(hero)], { stdio: 'inherit' });

  const mp4 = path.join(out, 'shubh-deepavali-reel.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', wav,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-maxrate', '2500k', '-bufsize', '5000k', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.1',
    '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', mp4], { stdio: ['pipe', 'inherit', 'inherit'] });

  const frames = Math.round(dur * FPS);
  for (let f = 0; f < frames; f++) {
    const b64 = await page.evaluate((t) => { render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.95).split(',')[1]; }, f / FPS);
    if (!ff.stdin.write(Buffer.from(b64, 'base64'))) await new Promise((r) => ff.stdin.once('drain', r));
    if (f % 90 === 0) process.stdout.write(`frame ${f}/${frames}\r`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));

  // still greeting card (finale frame) as a high-quality PNG
  await page.evaluate((h) => render(25.4 + h), hero);
  await page.locator('canvas').screenshot({ path: path.join(out, 'shubh-deepavali-card.png') });
  await page.evaluate(() => render(0));
  await page.locator('canvas').screenshot({ path: path.join(out, 'shubh-deepavali-thumbnail.png') });
  await browser.close();
  fs.unlinkSync(fwJson);
  console.log('\nwrote', mp4);
})();
