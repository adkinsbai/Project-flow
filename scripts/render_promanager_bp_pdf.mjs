import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/10990/.cache/ms-playwright-agent/node_modules/playwright');

const root = process.cwd();
const htmlPath = path.join(root, 'output', 'promanager-investor-bp.html');
const pdfPath = path.join(root, 'output', 'pdf', 'ProManager_Investor_BP_CN.pdf');

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 2200 }, deviceScaleFactor: 1 });
await page.goto('file:///' + htmlPath.replaceAll('\\', '/'), { waitUntil: 'networkidle' });
await page.emulateMedia({ media: 'print' });
await page.pdf({
  path: pdfPath,
  format: 'A4',
  printBackground: true,
  preferCSSPageSize: true,
  margin: { top: '0mm', right: '0mm', bottom: '0mm', left: '0mm' },
});
await browser.close();
console.log(pdfPath);
