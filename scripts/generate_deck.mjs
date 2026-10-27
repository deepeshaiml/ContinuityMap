import fs from 'node:fs/promises'
import path from 'node:path'
import PptxGenJS from 'pptxgenjs'

const root = path.resolve(import.meta.dirname, '..')
const outDir = root
await fs.mkdir(outDir, { recursive: true })

const deckContent = JSON.parse(await fs.readFile(path.join(root, 'data/deck_content.json'), 'utf8'))
const slides = deckContent.slides

const pptx = new PptxGenJS()
pptx.layout = 'LAYOUT_WIDE'
pptx.author = 'ContinuityMap'
pptx.subject = 'Evidence-backed infrastructure dependency and resilience planning'
pptx.title = 'ContinuityMap — AI-assisted critical infrastructure resilience planning'
pptx.company = 'ContinuityMap'
pptx.lang = 'en-US'
pptx.theme = { headFontFace: 'Aptos Display', bodyFontFace: 'Aptos', lang: 'en-US' }
pptx.defineSlideMaster({
  title: 'CM_LIGHT', background: { color: 'F3F6F7' },
  objects: [
    { rect: { x: 0, y: 0, w: 0.1, h: 7.5, line: { color: '087F8C', transparency: 100 }, fill: { color: '087F8C' } } },
    { line: { x: 0.55, y: 7.05, w: 12.25, h: 0, line: { color: 'DDE5E8', width: 0.7 } } },
    { text: { text: 'CONTINUITYMAP   ·   SYNTHETIC PLANNING DEMONSTRATION', options: { x: 0.6, y: 7.11, w: 8, h: 0.16, fontFace: 'Aptos', fontSize: 7.5, color: '71838D', charSpacing: 0.5, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.1, w: 0.45, h: 0.18, color: '71838D', fontFace: 'Aptos', fontSize: 8, align: 'right', margin: 0 },
})

const C = { navy: '102638', ink: '203747', muted: '72858D', teal: '087F8C', tealPale: 'E5F4F2', blue: '5E80AA', bluePale: 'EDF2F8', amber: 'B17B24', amberPale: 'FFF4DC', coral: 'C7543F', coralPale: 'FFF0EB', white: 'FFFFFF', line: 'E0E8EA', pale: 'F7FAFA' }
const W = 13.333, H = 7.5

function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, { x, y, w, h, margin: 0, breakLine: false, fontFace: opts.fontFace || 'Aptos', fontSize: opts.fontSize || 12, color: opts.color || C.ink, bold: opts.bold || false, valign: opts.valign || 'mid', fit: 'shrink', paraSpaceAfterPt: 0, ...opts })
}
function round(slide, x, y, w, h, fill, line = fill, radius = 0.12) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: radius, line: { color: line, width: 0.7 }, fill: { color: fill } })
}
function accentFor(key) { return key === 'amber' ? [C.amber, C.amberPale] : key === 'coral' ? [C.coral, C.coralPale] : key === 'blue' ? [C.blue, C.bluePale] : [C.teal, C.tealPale] }
function drawLight(slide, item, index) {
  const [accent, pale] = accentFor(item.accent)
  text(slide, item.section.toUpperCase(), 0.62, 0.32, 6.5, 0.2, { fontSize: 8, bold: true, charSpacing: 1.2, color: accent })
  text(slide, item.title, 0.62, 0.62, 12.0, 0.58, { fontFace: 'Aptos Display', fontSize: 25, bold: true, color: C.navy, valign: 'mid' })
  text(slide, item.subtitle, 0.64, 1.26, 11.9, 0.38, { fontSize: 12, color: C.muted, valign: 'top' })
  slide.addShape(pptx.ShapeType.line, { x: 0.62, y: 1.77, w: 12.1, h: 0, line: { color: C.line, width: 1 } })

  text(slide, 'PLANNING INSIGHT', 0.68, 2.02, 4.8, 0.2, { fontSize: 8, color: '91A0A6', bold: true, charSpacing: 0.9 })
  let bulletY = 2.36
  for (const bullet of item.bullets) {
    slide.addShape(pptx.ShapeType.ellipse, { x: 0.7, y: bulletY + 0.07, w: 0.09, h: 0.09, line: { color: accent, transparency: 100 }, fill: { color: accent } })
    text(slide, bullet, 0.92, bulletY, 4.62, 0.62, { fontSize: 13, color: C.ink, valign: 'top', breakLine: false, fit: 'shrink' })
    bulletY += 0.98
  }
  round(slide, 0.67, 5.66, 4.88, 0.8, pale, pale)
  text(slide, 'TAKEAWAY', 0.86, 5.81, 1.0, 0.16, { fontSize: 7.5, bold: true, color: accent, charSpacing: 0.9 })
  text(slide, item.takeaway, 0.86, 6.02, 4.49, 0.34, { fontSize: 10.3, color: C.ink, bold: true, valign: 'top' })

  round(slide, 5.92, 1.98, 6.75, 4.48, C.white, C.line)
  text(slide, item.visualTitle, 6.22, 2.18, 6.1, 0.3, { fontFace: 'Aptos Display', fontSize: 14, color: C.navy, bold: true })
  drawVisual(slide, item, 6.17, 2.7, 6.25, 3.48, accent, pale)
}

function drawVisual(slide, item, x, y, w, h, accent, pale) {
  const rows = item.visualItems
  if (item.visualStyle === 'flow') {
    const gap = 0.20, boxW = (w - 3 * gap - 0.54) / 4, boxH = 1.28, top = y + 0.8
    rows.forEach((row, i) => {
      const bx = x + i * (boxW + gap + 0.18)
      round(slide, bx, top, boxW, boxH, i === 0 ? pale : C.pale, i === 0 ? pale : C.line)
      slide.addShape(pptx.ShapeType.ellipse, { x: bx + 0.14, y: top + 0.16, w: 0.25, h: 0.25, line: { color: accent, transparency: 100 }, fill: { color: accent } })
      text(slide, row.title, bx + 0.14, top + 0.52, boxW - 0.24, 0.3, { fontSize: 11, bold: true, color: C.navy })
      text(slide, row.text, bx + 0.14, top + 0.84, boxW - 0.24, 0.32, { fontSize: 8.3, color: C.muted, valign: 'top' })
      if (i < rows.length - 1) text(slide, '›', bx + boxW + 0.015, top + 0.47, 0.2, 0.28, { fontSize: 19, bold: true, color: accent, align: 'center' })
    })
    return
  }
  if (item.visualStyle === 'record') {
    round(slide, x + 0.25, y + 0.46, w - 0.5, 2.35, pale, 'D7EBE7')
    const row = rows[0]
    text(slide, row.title, x + 0.5, y + 0.72, w - 1, 0.5, { fontFace: 'Aptos Display', fontSize: 18, bold: true, color: C.navy, valign: 'top' })
    text(slide, row.text, x + 0.5, y + 1.47, w - 1.03, 0.82, { fontSize: 11, color: C.ink, valign: 'top', breakLine: false })
    return
  }
  if (item.visualStyle === 'logic') {
    rows.forEach((row, i) => {
      const bx = x + i * 3.13
      round(slide, bx, y + 0.48, 2.88, 2.45, i === 0 ? 'F1F8F5' : 'F8F8F6', i === 0 ? 'DDEDE7' : 'EEE9DC')
      const [title, rule] = row.title.split('·')
      text(slide, title.trim(), bx + 0.2, y + 0.75, 1.3, 0.38, { fontSize: 14, bold: true, color: i === 0 ? C.teal : C.amber })
      text(slide, rule?.trim() || '', bx + 1.0, y + 0.78, 1.6, 0.3, { fontSize: 9, bold: true, color: C.muted, align: 'right' })
      text(slide, row.text, bx + 0.2, y + 1.35, 2.46, 1.0, { fontSize: 10, color: C.ink, valign: 'top' })
    })
    return
  }
  if (item.visualStyle === 'trace') {
    rows.forEach((row, i) => {
      const cy = y + 0.22 + i * 0.75
      if (i < rows.length - 1) slide.addShape(pptx.ShapeType.line, { x: x + 0.24, y: cy + 0.35, w: 0, h: 0.4, line: { color: i === 2 ? C.amber : accent, width: 1.6, beginArrowType: 'none', endArrowType: 'triangle' } })
      const current = i === 3 ? C.amber : i === 2 ? C.coral : accent
      slide.addShape(pptx.ShapeType.ellipse, { x, y: cy + 0.08, w: 0.17, h: 0.17, line: { color: current, width: 1 }, fill: { color: i === 3 ? C.amberPale : C.white } })
      round(slide, x + 0.42, cy, w - 0.55, 0.58, i === 3 ? C.amberPale : C.pale, i === 3 ? 'EDDBB5' : C.line)
      text(slide, row.title, x + 0.62, cy + 0.08, 1.45, 0.18, { fontSize: 8, bold: true, color: current, charSpacing: 0.4 })
      text(slide, row.text, x + 2.0, cy + 0.06, w - 2.34, 0.4, { fontSize: 9.5, color: C.ink })
    })
    return
  }
  if (item.visualStyle === 'compare') {
    rows.forEach((row, i) => {
      const cy = y + 0.54 + i * 1.35
      round(slide, x + 0.15, cy, w - 0.3, 1.08, i === 0 ? C.tealPale : C.bluePale, i === 0 ? 'D3E9E4' : 'DFE7F0')
      text(slide, row.title, x + 0.38, cy + 0.16, w - 0.8, 0.23, { fontSize: 10, bold: true, color: i === 0 ? C.teal : C.blue })
      text(slide, row.text, x + 0.38, cy + 0.48, w - 0.8, 0.38, { fontSize: 9.4, color: C.ink })
    })
    return
  }
  if (item.visualStyle === 'revenue') {
    text(slide, 'ORGANIZATIONS', x + 0.12, y + 0.22, 1.5, 0.17, { fontSize: 7.5, bold: true, color: C.muted, charSpacing: 0.7 })
    text(slide, 'YEAR-ONE REVENUE / GROSS PROFIT', x + 2.6, y + 0.22, 3.5, 0.17, { fontSize: 7.5, bold: true, color: C.muted, charSpacing: 0.55 })
    rows.forEach((row, i) => {
      const cy = y + 0.52 + i * 0.68
      round(slide, x + 0.05, cy, w - 0.1, 0.52, i % 2 ? 'F8FAFA' : 'F2F7F7', i % 2 ? 'F8FAFA' : 'F2F7F7')
      text(slide, row.title, x + 0.23, cy + 0.1, 1.6, 0.27, { fontSize: 10, bold: true, color: C.navy })
      text(slide, row.text, x + 2.0, cy + 0.1, 3.9, 0.27, { fontSize: 10, bold: true, color: C.teal })
    })
    text(slide, 'Model: $92k recurring + $28k onboarding · $30k direct year-one cost per organization.', x + 0.14, y + 3.26, w - 0.2, 0.2, { fontSize: 7.8, color: C.muted })
    return
  }
  if (item.visualStyle === 'timeline') {
    slide.addShape(pptx.ShapeType.line, { x: x + 0.3, y: y + 1.15, w: w - 0.6, h: 0, line: { color: 'CBDADD', width: 2 } })
    rows.forEach((row, i) => {
      const bx = x + i * 2.08
      slide.addShape(pptx.ShapeType.ellipse, { x: bx + 0.18, y: y + 1.02, w: 0.27, h: 0.27, line: { color: accent, width: 1 }, fill: { color: C.white } })
      round(slide, bx, y + 1.55, 1.92, 1.3, i === 0 ? pale : C.pale, i === 0 ? pale : C.line)
      text(slide, row.title, bx + 0.16, y + 1.73, 1.6, 0.3, { fontSize: 10, bold: true, color: accent })
      text(slide, row.text, bx + 0.16, y + 2.12, 1.6, 0.54, { fontSize: 8.2, color: C.ink, valign: 'top' })
    })
    return
  }
  const cols = rows.length > 3 ? 2 : rows.length
  const cardW = (w - 0.28 * (cols - 1)) / cols
  const cardH = rows.length > 3 ? 1.18 : 1.65
  rows.forEach((row, i) => {
    const rowIndex = Math.floor(i / cols), col = i % cols
    const bx = x + col * (cardW + 0.28), by = y + 0.35 + rowIndex * (cardH + 0.25)
    round(slide, bx, by, cardW, cardH, i === 0 ? pale : C.pale, i === 0 ? pale : C.line)
    slide.addShape(pptx.ShapeType.rect, { x: bx, y: by, w: 0.05, h: cardH, line: { color: accent, transparency: 100 }, fill: { color: accent } })
    text(slide, row.title, bx + 0.18, by + 0.17, cardW - 0.34, 0.25, { fontSize: 10, bold: true, color: C.navy, valign: 'top' })
    text(slide, row.text, bx + 0.18, by + 0.55, cardW - 0.34, cardH - 0.68, { fontSize: 9.2, color: C.muted, valign: 'top' })
  })
}

function drawCover(slide) {
  slide.background = { color: C.navy }
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.13, h: H, line: { color: C.teal, transparency: 100 }, fill: { color: C.teal } })
  text(slide, 'CONTINUITYMAP', 0.72, 0.62, 5.0, 0.25, { fontSize: 10, color: '70C8C4', bold: true, charSpacing: 2.0 })
  text(slide, 'Essential services\nrely on one another.', 0.72, 1.32, 8.5, 1.5, { fontFace: 'Aptos Display', fontSize: 31, bold: true, color: C.white, breakLine: false, valign: 'top' })
  text(slide, deckContent.subtitle, 0.74, 3.08, 8.0, 0.48, { fontSize: 15, color: 'CDDCE2' })
  text(slide, 'A reviewable map and simple what-if exercises, with evidence owners can check.', 0.74, 3.66, 8.3, 0.43, { fontSize: 12, color: 'AAC0CA' })
  const items = slides[0].visualItems.map((row) => [row.title.toUpperCase(), row.text])
  items.forEach(([label, name], i) => {
    const bx = 0.76 + i * 3.0
    round(slide, bx, 5.0, 2.55, 1.04, i === 0 ? '1C4050' : '193747', '355966')
    text(slide, label, bx + 0.16, 5.18, 2.15, 0.18, { fontSize: 8, color: '76C6C1', bold: true, charSpacing: 1.2 })
    text(slide, name, bx + 0.16, 5.49, 2.18, 0.3, { fontSize: 10.3, color: C.white, bold: true })
    if (i < items.length - 1) text(slide, '→', bx + 2.63, 5.37, 0.28, 0.27, { fontSize: 17, color: '79BFBA', bold: true, align: 'center' })
  })
  round(slide, 0.78, 6.64, 4.03, 0.36, '213F4D', '213F4D')
  text(slide, 'FICTIONAL DEMONSTRATION · PLANNING SUPPORT ONLY', 0.93, 6.74, 3.76, 0.12, { fontSize: 7, color: 'C5D5DB', bold: true, charSpacing: 0.65, align: 'center' })
  text(slide, '01', 12.25, 7.1, 0.45, 0.18, { fontSize: 8, color: '91A8B0', align: 'right' })
}

const cover = pptx.addSlide()
drawCover(cover)
cover.addNotes(slides[0].notes)
for (let i = 1; i < slides.length; i++) {
  const slide = pptx.addSlide('CM_LIGHT')
  drawLight(slide, slides[i], i + 1)
  slide.addNotes(slides[i].notes)
}

await pptx.writeFile({ fileName: path.join(outDir, 'ContinuityMap_Pitch_Deck.pptx') })
console.log(`Wrote ${slides.length} slides with speaker notes to ContinuityMap_Pitch_Deck.pptx`)
