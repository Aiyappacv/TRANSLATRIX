const { chromium } = require('playwright');
const SCRATCH = 'C:/Users/hp/AppData/Local/Temp/claude/f--TRANSLATRIX-TRANSLATRIX-PRO/d77909a4-24f6-47f9-91c6-79b99c02841a/scratchpad';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const consoleMsgs = [];
  const reqErrors = [];
  page.on('console', (msg) => consoleMsgs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', (err) => consoleMsgs.push('pageerror: ' + err.message));
  page.on('response', async (res) => {
    if (res.status() >= 400) {
      let body = '';
      try { body = await res.text(); } catch {}
      reqErrors.push(`${res.status()} ${res.url()} :: ${body.slice(0, 300)}`);
    }
  });

  const loginUrls = ['http://localhost:5174/auth/login', 'http://localhost:5173/auth/login'];
  let lastError = null;
  for (const url of loginUrls) {
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
      lastError = null;
      break;
    } catch (error) {
      lastError = error;
    }
  }
  if (lastError) throw lastError;
  await page.screenshot({ path: `${SCRATCH}/login_01_page.png` });

  await page.locator('input[type="email"]').first().fill('owner@translatrix.example.com');
  await page.locator('input[type="password"]').first().fill('DevOnly!2026');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SCRATCH}/login_02_after_submit.png` });
  console.log('URL after submit:', page.url());
  console.log('Console messages:', JSON.stringify(consoleMsgs, null, 2));
  console.log('Request errors:', JSON.stringify(reqErrors, null, 2));

  await browser.close();
})();
