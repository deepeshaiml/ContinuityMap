import { mkdir } from 'node:fs/promises'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'

const out = new URL('../reports/', import.meta.url)
await mkdir(out, { recursive: true })
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1760, height: 1120 }, deviceScaleFactor: 1 })
const errors = []
page.on('pageerror', (error) => errors.push(error.message))
page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })

try {
  const response = await page.goto('http://127.0.0.1:5174', { waitUntil: 'networkidle' })
  if (!response?.ok()) throw new Error(`Web app returned ${response?.status()}`)
  await page.getByText('Northbank Fictional Civic Services Network').waitFor()
  await page.locator('.cy-map canvas').first().waitFor()
  await page.getByRole('button', { name: 'Run scenario' }).click()
  await page.getByText(/Fixed fixture matches expected results/).waitFor()
  await page.screenshot({ path: new URL('ContinuityMap_Demo_Screenshot.png', out).pathname, fullPage: true })

  await page.getByRole('button', { name: /Prepare continuity brief/ }).click()
  await page.locator('.assessment-modal').waitFor()
  await page.screenshot({ path: new URL('ContinuityMap_Assessment_Screenshot.png', out).pathname, fullPage: true })

  const summary = await page.locator('.assessment-modal').innerText()
  if (!summary.includes('Affected services') || !summary.includes('Evidence gaps')) {
    throw new Error('Assessment is missing its expected evidence review sections')
  }
  if (errors.length) throw new Error(`Browser console errors: ${errors.join(' | ')}`)
  console.log(JSON.stringify({
    url: page.url(),
    fixture: await page.locator('.fixture-match').innerText(),
    assessmentSections: ['Affected services', 'Fallback resources', 'Evidence gaps', 'Suggested owner review actions'],
    screenshots: ['reports/ContinuityMap_Demo_Screenshot.png', 'reports/ContinuityMap_Assessment_Screenshot.png'],
  }, null, 2))
} finally {
  await browser.close()
}
