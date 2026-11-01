/**
 * Prize Coupon Draw — Google Sheets + Apps Script backend
 *
 * Every card number (100–1300) has ONE fixed hidden "draw number" (also 100–1300),
 * generated once as a random shuffle. The same list is used for:
 *   - ONLINE cards: shown as tiles on travelkannur.in/lottery/. A customer picks a card,
 *     enters name + phone, and the page reveals that card's hidden number.
 *   - PRINTED scratch cards: the Print tab lists card number + scratch number to print.
 * Because each card has exactly one number and each number belongs to exactly one card,
 * a sold card and its number can never be given to anyone else.
 *
 * Sheets:
 *   Settings – range, online range, open/closed, coupon codes, draw date text
 *   Pool     – every card: channel (online/printed), hidden number, sale status
 *   Print    – printed cards only: card number + scratch number, plus who bought it
 *   Draws    – one row per online sale (the official online result list)
 *   Log      – every event, hash-chained so later edits are detectable
 *   Codes    – optional one-time coupon codes
 */

const SHEETS = { settings: 'Settings', pool: 'Pool', print: 'Print', draws: 'Draws', log: 'Log', codes: 'Codes' };
const DRAW_HEADERS = ['Draw #', 'Card number', 'Draw number', 'Name', 'Phone', 'Coupon code', 'Sold at (local)', 'Sold at (UTC)', 'Online cards left before', 'Sale ID'];
const LOG_HEADERS = ['Time (UTC)', 'Event', 'Name', 'Phone', 'Coupon code', 'Card', 'Draw number', 'Details', 'Device', 'Hash'];
const POOL_HEADERS = ['Card number', 'Channel', 'Draw number (hidden)', 'Status', 'Draw #', 'Sold at (UTC)'];
const PRINT_HEADERS = ['Card number', 'Scratch number', 'Sold to (name)', 'Phone', 'Notes'];
const CODE_HEADERS = ['Code', 'Status', 'Used by phone', 'Used at (UTC)', 'Card'];
const STATUS_CACHE_KEY = 'status-v3';

// ---------------------------------------------------------------- web app

/** The customer page is travelkannur.in/lottery/. Opening the script URL directly just points there. */
function doGet() {
  return HtmlService.createHtmlOutput(
    '<p style="font-family:sans-serif;padding:24px">This is the lottery backend. The draw is at ' +
    '<a href="https://travelkannur.in/lottery/" target="_top">travelkannur.in/lottery/</a>.</p>'
  ).setTitle('Lottery backend');
}

/** JSON API for travelkannur.in/lottery/: POST text/plain JSON {action: "status" | "visit" | "draw", ...}. */
function doPost(e) {
  let out;
  try {
    const req = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (req.action === 'status') out = getStatus();
    else if (req.action === 'visit') { logVisit(req.device); out = { ok: true }; }
    else if (req.action === 'draw') out = draw(req);
    else out = { status: 'error', message: 'Unknown request.' };
  } catch (err) {
    out = { status: 'error', message: 'Bad request.' };
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

/** Online cards already sold, how many are left, and the page settings. Never includes hidden numbers. Cached 5 s. */
function getStatus() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get(STATUS_CACHE_KEY);
  if (hit) return JSON.parse(hit);
  const s = getSettings_();
  const rows = readPool_();
  const usedTiles = [];
  let left = 0, total = 0;
  rows.forEach(r => {
    if (r[1] !== 'online') return;
    total++;
    if (r[3] === 'available') left++; else usedTiles.push(r[0]);
  });
  const out = {
    open: s.open, left: left, total: total, min: s.min, max: s.max,
    onlineFrom: s.onlineFrom, onlineTo: s.onlineTo,
    title: s.title, drawInfo: s.drawInfo, requireCode: s.requireCode, usedTiles: usedTiles
  };
  try { cache.put(STATUS_CACHE_KEY, JSON.stringify(out), 5); } catch (e) {}
  return out;
}

function logVisit(device) {
  safeLog_('page_opened', {}, String(device || '').slice(0, 200));
}

/** A customer picked an online card. Marks it sold and reveals its fixed draw number. */
function draw(form) {
  form = form || {};
  const name = String(form.name || '').trim().slice(0, 80);
  const phone = normalizePhone_(form.phone);
  const code = String(form.code || '').trim().toUpperCase().slice(0, 40);
  const device = String(form.device || '').slice(0, 200);
  const tile = parseInt(form.tile, 10);
  const who = { name: name, phone: phone, code: code, tile: isNaN(tile) ? '' : tile };

  if (name.length < 2) { safeLog_('rejected_invalid_name', who, device); return { status: 'error', message: 'Please enter your name.' }; }
  if (!phone) { safeLog_('rejected_invalid_phone', who, device, String(form.phone || '').slice(0, 30)); return { status: 'error', message: 'Please enter a valid phone number (digits only, with country code if you have one).' }; }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) {
    safeLog_('rejected_busy', who, device);
    return { status: 'error', message: 'The draw is very busy right now. Please wait a few seconds and try again.' };
  }
  try {
    const s = getSettings_();
    if (!s.open) { log_('rejected_draw_closed', who, device); return { status: 'closed', message: 'Online sales are closed right now.' }; }
    if (isNaN(tile) || tile < s.onlineFrom || tile > s.onlineTo) { log_('rejected_not_online_card', who, device); return { status: 'error', message: 'That card isn\'t sold online. Please choose a card from the list.' }; }

    // One card per phone number
    const draws = sheet_(SHEETS.draws);
    const dn = draws.getLastRow() - 1;
    if (dn > 0) {
      const prior = draws.getRange(2, 1, dn, 5).getValues().find(r => String(r[4]) === phone);
      if (prior) {
        log_('repeat_attempt_returned_existing', who, device, 'already has card ' + prior[1], prior[2]);
        return { status: 'existing', tile: prior[1], number: prior[2], drawNo: prior[0] };
      }
    }

    // Optional one-time coupon codes
    let codeRow = -1;
    if (s.requireCode) {
      if (!code) { log_('rejected_missing_code', who, device); return { status: 'error', message: 'Please enter the code from your coupon.' }; }
      const codes = sheet_(SHEETS.codes);
      const cn = codes.getLastRow() - 1;
      const list = cn > 0 ? codes.getRange(2, 1, cn, 2).getValues() : [];
      const i = list.findIndex(r => String(r[0]).toUpperCase() === code);
      if (i < 0) { log_('rejected_unknown_code', who, device); return { status: 'error', message: 'That coupon code isn\'t valid. Check it and try again.' }; }
      if (list[i][1] !== 'unused') { log_('rejected_code_already_used', who, device); return { status: 'error', message: 'That coupon code has already been used.' }; }
      codeRow = i + 2;
    }

    const pool = sheet_(SHEETS.pool);
    const rows = readPool_();
    const ti = rows.findIndex(r => r[0] === tile);
    if (ti < 0 || rows[ti][1] !== 'online') { log_('rejected_not_online_card', who, device); return { status: 'error', message: 'That card isn\'t sold online.' }; }
    if (rows[ti][3] !== 'available') {
      log_('rejected_card_taken', who, device);
      return {
        status: 'tile_taken',
        message: 'Someone just took card ' + tile + '. Please choose another card.',
        usedTiles: rows.filter(r => r[1] === 'online' && r[3] !== 'available').map(r => r[0])
      };
    }

    const number = rows[ti][2];
    const leftBefore = rows.filter(r => r[1] === 'online' && r[3] === 'available').length;
    const now = new Date();
    const utc = now.toISOString();
    const local = Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
    const drawNo = dn + 1;
    const saleId = Utilities.getUuid();

    pool.getRange(ti + 2, 4, 1, 3).setValues([['sold online', drawNo, utc]]);
    draws.appendRow([drawNo, tile, number, name, "'" + phone, code, local, utc, leftBefore, saleId]);
    if (codeRow > 0) sheet_(SHEETS.codes).getRange(codeRow, 2, 1, 4).setValues([['used', "'" + phone, utc, tile]]);
    log_('card_sold_online', who, device, 'card ' + tile + ' revealed ' + number + ', draw #' + drawNo + ', ' + leftBefore + ' online cards left before, id ' + saleId, number);
    SpreadsheetApp.flush();
    CacheService.getScriptCache().remove(STATUS_CACHE_KEY);
    return { status: 'assigned', tile: tile, number: number, drawNo: drawNo, left: leftBefore - 1 };
  } catch (err) {
    try { log_('error', who, device, String(err && err.message || err).slice(0, 300)); } catch (e) {}
    return { status: 'error', message: 'Something went wrong on our side. Please try again in a moment.' };
  } finally {
    lock.releaseLock();
  }
}

// ---------------------------------------------------------------- admin menu

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Lottery')
    .addItem('Find who holds a draw number…', 'findHolder')
    .addItem('Run integrity check', 'integrityCheck')
    .addItem('Open online sales', 'openDraw')
    .addItem('Close online sales', 'closeDraw')
    .addSeparator()
    .addItem('Generate coupon codes…', 'generateCodes')
    .addSeparator()
    .addItem('Set up (first time) / clear online sales…', 'setup')
    .addItem('Generate new card numbers (before printing only)…', 'regenerateNumbers')
    .addToUi();
}

/**
 * First run: creates all tabs and the fixed card → number list.
 * Later runs: clears online sales and the log but KEEPS the card numbers, so printed cards stay valid.
 */
function setup() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActive();
  const props = PropertiesService.getScriptProperties();
  props.setProperty('SHEET_ID', ss.getId());

  const existing = ss.getSheetByName(SHEETS.draws);
  if (existing && existing.getLastRow() > 1) {
    const r = ui.alert('Clear online sales?', 'This erases all ' + (existing.getLastRow() - 1) + ' online sales and the log, and makes every online card available again. Card numbers and scratch numbers stay the same. This cannot be undone; download a copy first if you need the records.', ui.ButtonSet.YES_NO);
    if (r !== ui.Button.YES) return;
  }

  const settings = getOrCreate_(ss, SHEETS.settings);
  if (settings.getLastRow() < 2) {
    settings.clear();
    settings.getRange(1, 1, 10, 3).setValues([
      ['Setting', 'Value', 'What it does'],
      ['title', 'Prize Coupon Draw', 'Name shown at the top of the customer page'],
      ['min', 100, 'Lowest card / draw number'],
      ['max', 1300, 'Highest card / draw number'],
      ['online_from', 100, 'First card number sold online'],
      ['online_to', 699, 'Last card number sold online (the rest are printed scratch cards)'],
      ['open', true, 'TRUE = online sales open, FALSE = closed'],
      ['require_code', false, 'TRUE = customers must enter a one-time coupon code from the Codes sheet'],
      ['draw_info', 'Draw: 21 January, 10 pm', 'Line shown under the banner on the customer page'],
      ['numbers_locked', false, 'Set to TRUE once cards are sent for printing; blocks regenerating numbers']
    ]);
    settings.setFrozenRows(1);
    settings.getRange('A1:C1').setFontWeight('bold');
    settings.autoResizeColumns(1, 3);
  }
  const s = getSettings_();

  const pool = ss.getSheetByName(SHEETS.pool);
  const hasNumbers = pool && pool.getLastRow() - 1 === s.max - s.min + 1 && props.getProperty('MAPPING_HASH');
  if (!hasNumbers) {
    writeNewNumbers_(ss, s);
  } else {
    // keep numbers, clear online sales
    const n = pool.getLastRow() - 1;
    const rows = pool.getRange(2, 1, n, 6).getValues().map(r => [r[0], r[1], r[2], r[1] === 'online' ? 'available' : 'printed', '', '']);
    pool.getRange(2, 1, n, 6).setValues(rows);
  }

  resetSheet_(ss, SHEETS.draws, DRAW_HEADERS);
  resetSheet_(ss, SHEETS.log, LOG_HEADERS);
  if (!ss.getSheetByName(SHEETS.codes)) resetSheet_(ss, SHEETS.codes, CODE_HEADERS);
  props.setProperty('LAST_HASH', 'GENESIS');
  CacheService.getScriptCache().remove(STATUS_CACHE_KEY);

  [SHEETS.pool, SHEETS.draws, SHEETS.log].forEach(name => {
    const sh = ss.getSheetByName(name);
    sh.getProtections(SpreadsheetApp.ProtectionType.SHEET).forEach(p => p.remove());
    sh.protect().setDescription('Written by the lottery script — edits would break the audit').setWarningOnly(true);
  });

  log_(hasNumbers ? 'online_sales_cleared' : 'lottery_created', {}, '',
    'cards ' + s.min + '–' + s.max + ', online ' + s.onlineFrom + '–' + s.onlineTo + ', numbers fingerprint ' + props.getProperty('MAPPING_HASH').slice(0, 16));
  const def = ss.getSheetByName('Sheet1');
  if (def && def.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(def);
  ui.alert('Ready',
    (hasNumbers ? 'Online sales cleared. Card numbers are unchanged.' :
      'Card numbers and hidden draw numbers created for ' + s.min + '–' + s.max + '. Online: ' + s.onlineFrom + '–' + s.onlineTo + '. The Print tab lists the scratch cards to print.') +
    '\n\nIf you have not deployed yet: Deploy → New deployment → Web app, Execute as: Me, Who has access: Anyone.',
    ui.ButtonSet.OK);
}

/** Replaces every card's hidden number. Only allowed before cards are printed. */
function regenerateNumbers() {
  const ui = SpreadsheetApp.getUi();
  const s = getSettings_();
  if (s.numbersLocked) { ui.alert('Numbers are locked', 'Settings → numbers_locked is TRUE, so the card numbers can no longer change. Printed cards depend on them.', ui.ButtonSet.OK); return; }
  const draws = sheet_(SHEETS.draws);
  if (draws.getLastRow() > 1) { ui.alert('Online sales exist', 'Cards have already been sold online. Clear online sales first (Set up / clear online sales).', ui.ButtonSet.OK); return; }
  const r = ui.prompt('Generate new card numbers', 'Every hidden draw number will change and the Print tab will be rewritten. Only do this BEFORE cards are printed.\n\nType NEW NUMBERS to confirm:', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK || r.getResponseText().trim().toUpperCase() !== 'NEW NUMBERS') return;
  const lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    writeNewNumbers_(SpreadsheetApp.getActive(), s);
    log_('numbers_regenerated_by_admin', {}, '', 'numbers fingerprint ' + PropertiesService.getScriptProperties().getProperty('MAPPING_HASH').slice(0, 16));
    CacheService.getScriptCache().remove(STATUS_CACHE_KEY);
  } finally { lock.releaseLock(); }
  ui.alert('New card numbers created. The Print tab has been rewritten.');
}

function writeNewNumbers_(ss, s) {
  const values = [];
  for (let n = s.min; n <= s.max; n++) values.push(n);
  // Fisher–Yates shuffle with an unbiased secure random source
  const hidden = values.slice();
  for (let i = hidden.length - 1; i > 0; i--) {
    const j = secureRandomInt_(i + 1);
    const t = hidden[i]; hidden[i] = hidden[j]; hidden[j] = t;
  }
  const poolRows = values.map((card, i) => {
    const online = card >= s.onlineFrom && card <= s.onlineTo;
    return [card, online ? 'online' : 'printed', hidden[i], online ? 'available' : 'printed', '', ''];
  });
  const pool = resetSheet_(ss, SHEETS.pool, POOL_HEADERS);
  pool.getRange(2, 1, poolRows.length, POOL_HEADERS.length).setValues(poolRows);

  const printRows = poolRows.filter(r => r[1] === 'printed').map(r => [r[0], r[2], '', '', '']);
  const print = resetSheet_(ss, SHEETS.print, PRINT_HEADERS);
  if (printRows.length) {
    print.getRange(2, 1, printRows.length, PRINT_HEADERS.length).setValues(printRows);
    print.getRange(2, 4, printRows.length, 1).setNumberFormat('@');
    print.protect().setDescription('Card and scratch numbers are fixed; only fill Sold to / Phone / Notes')
      .setUnprotectedRanges([print.getRange(2, 3, printRows.length, 3)]).setWarningOnly(true);
  }
  print.autoResizeColumns(1, 2);
  PropertiesService.getScriptProperties().setProperty('MAPPING_HASH', mappingHash_(poolRows));
}

function openDraw() { setSetting_('open', true); log_('sales_opened_by_admin', {}, ''); SpreadsheetApp.getUi().alert('Online sales are open.'); }
function closeDraw() { setSetting_('open', false); log_('sales_closed_by_admin', {}, ''); SpreadsheetApp.getUi().alert('Online sales are closed. Customers will see a "closed" message.'); }

/** On draw night: type a winning draw number, see which card holds it and who bought it. */
function findHolder() {
  const ui = SpreadsheetApp.getUi();
  const r = ui.prompt('Find who holds a draw number', 'Type the winning draw number (the hidden / scratch number):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  const num = parseInt(r.getResponseText(), 10);
  const row = readPool_().find(x => x[2] === num);
  if (!row) { ui.alert('No card has draw number ' + r.getResponseText().trim() + '.'); return; }
  const card = row[0];
  let msg = 'Draw number ' + num + ' is on card ' + card + ' (' + (row[1] === 'online' ? 'sold online' : 'printed scratch card') + ').\n\n';
  if (row[1] === 'online') {
    const d = sheet_(SHEETS.draws), dn = d.getLastRow() - 1;
    const sale = dn > 0 ? d.getRange(2, 1, dn, 8).getValues().find(x => x[1] === card) : null;
    msg += sale ? 'Bought by ' + sale[3] + ', phone ' + sale[4] + ', on ' + sale[6] + ' (draw #' + sale[0] + ').' : 'This online card has NOT been sold.';
  } else {
    const p = sheet_(SHEETS.print), pn = p.getLastRow() - 1;
    const pr = pn > 0 ? p.getRange(2, 1, pn, 5).getDisplayValues().find(x => Number(x[0]) === card) : null;
    msg += pr && (pr[2] || pr[3]) ? 'Recorded as sold to ' + (pr[2] || '—') + ', phone ' + (pr[3] || '—') + (pr[4] ? ' (' + pr[4] + ')' : '') + '.' : 'No buyer is recorded in the Print tab. The holder must show the physical card with card number ' + card + '.';
  }
  log_('holder_lookup_by_admin', { tile: card }, '', 'draw number ' + num, num);
  ui.alert('Draw number ' + num, msg, ui.ButtonSet.OK);
}

function generateCodes() {
  const ui = SpreadsheetApp.getUi();
  const r = ui.prompt('Generate coupon codes', 'How many one-time codes? (1–2000)', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  const n = Math.min(2000, Math.max(1, parseInt(r.getResponseText(), 10) || 0));
  const codes = sheet_(SHEETS.codes);
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const rows = [];
  for (let i = 0; i < n; i++) {
    let c = '';
    for (let j = 0; j < 8; j++) c += alphabet[secureRandomInt_(alphabet.length)];
    rows.push([c.slice(0, 4) + '-' + c.slice(4), 'unused', '', '', '']);
  }
  codes.getRange(codes.getLastRow() + 1, 1, n, 5).setValues(rows);
  log_('codes_generated_by_admin', {}, '', n + ' codes');
  ui.alert(n + ' codes added to the Codes sheet. Set require_code to TRUE in Settings to make customers use them.');
}

function integrityCheck() {
  const ui = SpreadsheetApp.getUi();
  const s = getSettings_();
  const issues = [];
  const pool = sheet_(SHEETS.pool);
  const pn = pool.getLastRow() - 1;
  const pv = pn > 0 ? pool.getRange(2, 1, pn, 6).getValues() : [];

  // 1. The card → number list is a true one-to-one shuffle and has not changed since it was made
  const seenHidden = {}, numberOf = {};
  pv.forEach(r => {
    if (seenHidden[r[2]]) issues.push('Draw number ' + r[2] + ' is on two cards (' + seenHidden[r[2]] + ' and ' + r[0] + ').');
    seenHidden[r[2]] = r[0]; numberOf[r[0]] = r[2];
  });
  for (let n = s.min; n <= s.max; n++) {
    if (numberOf[n] === undefined) issues.push('Card ' + n + ' is missing from Pool.');
    if (!seenHidden[n]) issues.push('Draw number ' + n + ' is not on any card.');
  }
  const stored = PropertiesService.getScriptProperties().getProperty('MAPPING_HASH');
  if (stored && mappingHash_(pv) !== stored) issues.push('The card → draw number list in Pool was changed after it was created.');

  // 2. Printed cards match Pool
  const print = sheet_(SHEETS.print);
  const prn = print.getLastRow() - 1;
  (prn > 0 ? print.getRange(2, 1, prn, 2).getValues() : []).forEach(r => {
    if (numberOf[r[0]] !== r[1]) issues.push('Print tab: card ' + r[0] + ' shows scratch number ' + r[1] + ', but Pool says ' + numberOf[r[0]] + '.');
  });

  // 3. Online sales
  const draws = sheet_(SHEETS.draws);
  const dn = draws.getLastRow() - 1;
  const d = dn > 0 ? draws.getRange(2, 1, dn, 5).getValues() : [];
  const seenCard = {}, seenPhone = {};
  d.forEach((r, i) => {
    const no = r[0], card = r[1], num = r[2], phone = String(r[4]);
    if (no !== i + 1) issues.push('Draws row ' + (i + 2) + ': draw # is ' + no + ', expected ' + (i + 1) + '.');
    if (card < s.onlineFrom || card > s.onlineTo) issues.push('Card ' + card + ' was sold online but is outside the online range.');
    if (numberOf[card] !== num) issues.push('Card ' + card + ' revealed ' + num + ', but its fixed draw number is ' + numberOf[card] + '.');
    if (seenCard[card]) issues.push('Card ' + card + ' was sold twice (draws #' + seenCard[card] + ' and #' + no + ').');
    if (seenPhone[phone]) issues.push('Phone ' + phone + ' bought twice (draws #' + seenPhone[phone] + ' and #' + no + ').');
    seenCard[card] = no; seenPhone[phone] = no;
  });
  let soldInPool = 0;
  pv.forEach(r => {
    if (r[3] === 'sold online') { soldInPool++; if (!seenCard[r[0]]) issues.push('Card ' + r[0] + ' is marked sold in Pool but has no row in Draws.'); }
    else if (seenCard[r[0]]) issues.push('Card ' + r[0] + ' is in Draws but not marked sold in Pool.');
  });

  // 4. Log hash chain
  const log = sheet_(SHEETS.log);
  const ln = log.getLastRow() - 1;
  let brokenAt = 0;
  if (ln > 0) {
    const lv = log.getRange(2, 1, ln, LOG_HEADERS.length).getDisplayValues();
    let prev = 'GENESIS';
    for (let i = 0; i < lv.length; i++) {
      const hsh = chainHash_(prev, lv[i].slice(0, LOG_HEADERS.length - 1));
      if (hsh !== lv[i][LOG_HEADERS.length - 1]) { brokenAt = i + 2; break; }
      prev = hsh;
    }
  }
  if (brokenAt) issues.push('Log row ' + brokenAt + ' (or one right before it) was edited, deleted or reordered after it was written.');
  const soldInLog = ln > 0 ? log.getRange(2, 2, ln, 1).getValues().filter(r => r[0] === 'card_sold_online').length : 0;
  if (soldInLog !== d.length) issues.push('Log shows ' + soldInLog + ' online sales, but Draws has ' + d.length + ' rows.');

  log_('integrity_check_by_admin', {}, '', issues.length ? issues.length + ' issue(s)' : 'passed');
  const onlineTotal = pv.filter(r => r[1] === 'online').length;
  const summary = d.length + ' of ' + onlineTotal + ' online cards sold, ' + (pv.length - onlineTotal) + ' printed cards, ' + ln + ' log entries.\n\n';
  ui.alert(issues.length ? 'Integrity check: ' + issues.length + ' issue(s)' : 'Integrity check passed',
    summary + (issues.length ? issues.slice(0, 25).join('\n') : 'Every card has its own draw number and none has changed, the Print tab matches, every online card was sold once, every phone bought once, and the log hash chain is unbroken.'),
    ui.ButtonSet.OK);
}

// ---------------------------------------------------------------- helpers

function ss_() {
  const id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActive();
}
function sheet_(name) {
  const sh = ss_().getSheetByName(name);
  if (!sh) throw new Error('Missing sheet "' + name + '". Run Lottery → Set up first.');
  return sh;
}
/** [card, channel, hiddenNumber, status] per row */
function readPool_() {
  const pool = sheet_(SHEETS.pool);
  const n = pool.getLastRow() - 1;
  return n > 0 ? pool.getRange(2, 1, n, 4).getValues() : [];
}
function mappingHash_(rows) {
  return chainHash_('MAPPING', rows.map(r => r[0] + ':' + r[2]));
}
function getOrCreate_(ss, name) { return ss.getSheetByName(name) || ss.insertSheet(name); }
function resetSheet_(ss, name, headers) {
  const sh = getOrCreate_(ss, name);
  sh.getProtections(SpreadsheetApp.ProtectionType.SHEET).forEach(p => p.remove());
  sh.clear();
  sh.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
  sh.setFrozenRows(1);
  return sh;
}

function getSettings_() {
  const sh = ss_().getSheetByName(SHEETS.settings);
  const map = {};
  if (sh && sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(r => map[String(r[0]).trim()] = r[1]);
  const bool = v => v === true || String(v).toUpperCase() === 'TRUE';
  const min = parseInt(map.min, 10) || 100, max = parseInt(map.max, 10) || 1300;
  const half = min + Math.floor((max - min + 1) / 2) - 1;
  return {
    title: String(map.title || 'Prize Coupon Draw'),
    min: min, max: max,
    onlineFrom: parseInt(map.online_from, 10) || min,
    onlineTo: parseInt(map.online_to, 10) || half,
    open: map.open === undefined ? true : bool(map.open),
    requireCode: bool(map.require_code),
    drawInfo: String(map.draw_info || ''),
    numbersLocked: bool(map.numbers_locked)
  };
}
function setSetting_(key, value) {
  const sh = sheet_(SHEETS.settings);
  const keys = sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues();
  const i = keys.findIndex(r => r[0] === key);
  if (i >= 0) sh.getRange(i + 2, 2).setValue(value);
  CacheService.getScriptCache().remove(STATUS_CACHE_KEY);
}

function normalizePhone_(raw) {
  const s = String(raw || '').trim();
  const digits = s.replace(/\D/g, '');
  if (digits.length < 6 || digits.length > 15) return '';
  return (s.charAt(0) === '+' ? '+' : '') + digits;
}

/** Unbiased random integer in [0, max) from SHA-256 of a fresh UUID. */
function secureRandomInt_(max) {
  const limit = Math.floor(4294967296 / max) * max;
  for (;;) {
    const b = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, Utilities.getUuid() + Date.now() + Math.random());
    const v = (b[0] & 255) * 16777216 + (b[1] & 255) * 65536 + (b[2] & 255) * 256 + (b[3] & 255);
    if (v < limit) return v % max;
  }
}

function chainHash_(prev, fields) {
  const bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, prev + '|' + fields.join('|'), Utilities.Charset.UTF_8);
  return bytes.map(b => ('0' + (b & 255).toString(16)).slice(-2)).join('');
}

/** Appends one hash-chained log row. Must be called while holding the script lock (or from the admin menu). */
function log_(event, who, device, details, number) {
  who = who || {};
  const log = sheet_(SHEETS.log);
  const props = PropertiesService.getScriptProperties();
  const prev = props.getProperty('LAST_HASH') || 'GENESIS';
  const fields = [new Date().toISOString(), event, who.name || '', who.phone || '', who.code || '',
    who.tile === undefined ? '' : who.tile,
    number === undefined || number === '' ? '' : number,
    details || '', device || ''].map(String);
  const hash = chainHash_(prev, fields);
  const range = log.getRange(log.getLastRow() + 1, 1, 1, LOG_HEADERS.length);
  range.setNumberFormat('@'); // plain text, so the integrity check reads back exactly what was hashed
  range.setValues([fields.concat([hash])]);
  props.setProperty('LAST_HASH', hash);
}

/** Logs from outside a sale (e.g. page opens), taking the lock briefly. */
function safeLog_(event, who, device, details) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return;
  try { log_(event, who, device, details); } catch (e) {} finally { lock.releaseLock(); }
}
