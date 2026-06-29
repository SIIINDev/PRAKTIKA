// Capture GUI demonstration screenshots using Playwright's bundled Chromium.
// No system browser (no Edge/Chrome) required. Run: node capture-demo.mjs
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

// Screenshots go to <repo>/.context/gui-demo (gitignored — no binaries in the repo).
const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, '../../.context/gui-demo');
const UI = 'http://localhost:8080';
const API_DOCS = 'http://localhost:8000/docs';
mkdirSync(OUT, { recursive: true });

const log = (m) => console.log(m);

async function search(page, q) {
  await page.getByTestId('search-input').fill(q);
  await page.getByTestId('search-input').press('Enter');
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

// 1. Документы view
await page.goto(UI, { waitUntil: 'networkidle' });
await page.getByTestId('doc-list').waitFor({ timeout: 15000 }).catch(() => {});
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/01-documents.png` });
log('01-documents.png');

// 2. Search with Russian highlight
await page.getByTestId('nav-search').click();
await search(page, 'нейронные сети');
await page.getByTestId('result-card').first().waitFor({ timeout: 15000 });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/02-search-highlight.png`, fullPage: true });
log('02-search-highlight.png');

// 3. Broad query -> many results + pagination
await search(page, 'model');
await page.getByTestId('result-card').first().waitFor({ timeout: 15000 });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/03-search-english-highlight.png`, fullPage: true });
log('03-search-english-highlight.png');

// 4. Pagination -> page 2
const page2 = page.getByTestId('pagination').getByRole('button', { name: 'Страница 2', exact: true });
if (await page2.count()) {
  await page2.first().click();
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/04-pagination-page2.png`, fullPage: true });
  log('04-pagination-page2.png');
} else {
  log('04 skipped: pagination "2" not found');
}

// 5. Empty state
await search(page, 'zzzнетакого123');
await page.getByTestId('empty-state').waitFor({ timeout: 10000 });
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}/05-empty-state.png` });
log('05-empty-state.png');

// 6. Responsive 320px (with results visible)
await search(page, 'нейронные сети');
await page.getByTestId('result-card').first().waitFor({ timeout: 15000 });
await page.setViewportSize({ width: 320, height: 720 });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/06-responsive-320.png` });
log('06-responsive-320.png');

// 7. Swagger UI
const page2tab = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page2tab.goto(API_DOCS, { waitUntil: 'networkidle' });
await page2tab.locator('.opblock, #swagger-ui').first().waitFor({ timeout: 15000 }).catch(() => {});
await page2tab.waitForTimeout(1000);
await page2tab.screenshot({ path: `${OUT}/07-swagger.png` });
log('07-swagger.png');

await browser.close();
log('done');
