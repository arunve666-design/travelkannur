/**
 * Coupon Number Draw — public lottery on Google Sheets + Apps Script
 *
 * Customers open the web-app link, enter name + phone (and a coupon code if you
 * turn that on), tap Draw, and get one unique random number from the pool.
 * Every number can be drawn once. Every action is written to the Log sheet with
 * a tamper-evident hash chain, so the organizer can audit everything.
 *
 * Sheets created by setup():
 *   Settings – draw open/closed, number range, coupon-code requirement
 *   Pool     – every number and whether it's still available
 *   Draws    – one row per number given out (the official result list)
 *   Log      – every event: page opens, draws, repeats, rejections, errors
 *   Codes    – optional one-time coupon codes
 */

const SHEETS = { settings: 'Settings', pool: 'Pool', draws: 'Draws', log: 'Log', codes: 'Codes' };
const DRAW_HEADERS = ['Draw #', 'Number', 'Name', 'Phone', 'Coupon code', 'Drawn at (local)', 'Drawn at (UTC)', 'Numbers left before draw', 'Draw ID'];
const LOG_HEADERS = ['Time (UTC)', 'Event', 'Name', 'Phone', 'Coupon code', 'Number', 'Details', 'Device', 'Hash'];
const POOL_HEADERS = ['Number', 'Status', 'Draw #', 'Drawn at (UTC)'];
const CODE_HEADERS = ['Code', 'Status', 'Used by phone', 'Used at (UTC)', 'Number'];

// ---------------------------------------------------------------- web app

function doGet() {
  const s = getSettings_();
  const t = HtmlService.createTemplateFromFile('Index');
  t.title = s.title;
  t.requireCode = s.requireCode;
  t.min = s.min;
  t.max = s.max;
  return t.evaluate()
    .setTitle(s.title)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1, viewport-fit=cover')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DEFAULT);
}

/** Called from the page: how many numbers are left and whether the draw is open. */
function getStatus() {
  const s = getSettings_();
  const pool = sheet_(SHEETS.pool);
  const n = pool.getLastRow() - 1;
  const statuses = n > 0 ? pool.getRange(2, 2, n, 1).getValues() : [];
  const left = statuses.filter(r => r[0] === 'available').length;
  return { open: s.open, left: left, total: s.max - s.min + 1, min: s.min, max: s.max, title: s.title, requireCode: s.requireCode };
}

/**
 * JSON API used by the page hosted on travelkannur.in/lottery/.
 * The page POSTs a text/plain JSON body: {action: "status" | "visit" | "draw", ...}.
 */
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

/** Called from the page after it loads, so the visit is logged without slowing the page. */
function logVisit(device) {
  safeLog_('page_opened', {}, String(device || '').slice(0, 200));
}

/** Called from the page when a customer taps Draw. */
function draw(form) {
  form = form || {};
  const name = String(form.name || '').trim().slice(0, 80);
  const phone = normalizePhone_(form.phone);
  const code = String(form.code || '').trim().toUpperCase().slice(0, 40);
  const device = String(form.device || '').slice(0, 200);
  const who = { name: name, phone: phone, code: code };

  if (name.length < 2) { safeLog_('rejected_invalid_name', who, device); return { status: 'error', message: 'Please enter your name.' }; }
  if (!phone) { safeLog_('rejected_invalid_phone', who, device, String(form.phone || '').slice(0, 30)); return { status: 'error', message: 'Please enter a valid phone number (digits only, with country code if you have one).' }; }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) {
    safeLog_('rejected_busy', who, device);
    return { status: 'error', message: 'The draw is very busy right now. Please wait a few seconds and try again.' };
  }
  try {
    const s = getSettings_();
    if (!s.open) { log_('rejected_draw_closed', who, device); return { status: 'error', message: 'The draw is closed right now.' }; }

    // One number per phone number
    const draws = sheet_(SHEETS.draws);
    const dn = draws.getLastRow() - 1;
    if (dn > 0) {
      const rows = draws.getRange(2, 1, dn, 4).getValues();
      const prior = rows.find(r => String(r[3]) === phone);
      if (prior) {
        log_('repeat_attempt_returned_existing', who, device, '', prior[1]);
        return { status: 'existing', number: prior[1], drawNo: prior[0] };
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

    // Pick a random available number
    const pool = sheet_(SHEETS.pool);
    const pn = pool.getLastRow() - 1;
    const poolVals = pool.getRange(2, 1, pn, 2).getValues();
    const available = [];
    poolVals.forEach((r, i) => { if (r[1] === 'available') available.push(i); });
    if (!available.length) { log_('rejected_pool_empty', who, device); return { status: 'empty', message: 'Every number has been drawn. The pool is empty.' }; }

    const pick = available[secureRandomInt_(available.length)];
    const number = poolVals[pick][0];
    const now = new Date();
    const utc = now.toISOString();
    const local = Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
    const drawNo = dn + 1;
    const drawId = Utilities.getUuid();

    pool.getRange(pick + 2, 2, 1, 3).setValues([['drawn', drawNo, utc]]);
    draws.appendRow([drawNo, number, name, "'" + phone, code, local, utc, available.length, drawId]);
    if (codeRow > 0) sheet_(SHEETS.codes).getRange(codeRow, 2, 1, 4).setValues([['used', "'" + phone, utc, number]]);
    log_('number_assigned', who, device, 'draw #' + drawNo + ', ' + available.length + ' left before, id ' + drawId, number);
    SpreadsheetApp.flush();
    return { status: 'assigned', number: number, drawNo: drawNo, left: available.length - 1 };
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
    .addItem('Run integrity check', 'integrityCheck')
    .addItem('Open the draw', 'openDraw')
    .addItem('Close the draw', 'closeDraw')
    .addSeparator()
    .addItem('Generate coupon codes…', 'generateCodes')
    .addSeparator()
    .addItem('Set up / reset (erases draws)…', 'setup')
    .addToUi();
}

function setup() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActive();
  PropertiesService.getScriptProperties().setProperty('SHEET_ID', ss.getId());

  const existing = ss.getSheetByName(SHEETS.draws);
  if (existing && existing.getLastRow() > 1) {
    const r = ui.alert('Reset the lottery?', 'This erases all ' + (existing.getLastRow() - 1) + ' draws and the log, and puts every number back in the pool. This cannot be undone. Export or copy the sheet first if you need the records.', ui.ButtonSet.YES_NO);
    if (r !== ui.Button.YES) return;
  }

  const settings = getOrCreate_(ss, SHEETS.settings);
  if (settings.getLastRow() < 2) {
    settings.clear();
    settings.getRange(1, 1, 6, 3).setValues([
      ['Setting', 'Value', 'What it does'],
      ['title', 'Coupon Number Draw', 'Name shown at the top of the customer page'],
      ['min', 100, 'Lowest number in the pool'],
      ['max', 1300, 'Highest number in the pool'],
      ['open', true, 'TRUE = customers can draw, FALSE = draw is closed'],
      ['require_code', false, 'TRUE = customers must enter a one-time coupon code from the Codes sheet']
    ]);
    settings.setFrozenRows(1);
    settings.getRange('A1:C1').setFontWeight('bold');
    settings.autoResizeColumns(1, 3);
  }
  const s = getSettings_();

  const pool = resetSheet_(ss, SHEETS.pool, POOL_HEADERS);
  const rows = [];
  for (let n = s.min; n <= s.max; n++) rows.push([n, 'available', '', '']);
  pool.getRange(2, 1, rows.length, 4).setValues(rows);

  resetSheet_(ss, SHEETS.draws, DRAW_HEADERS);
  resetSheet_(ss, SHEETS.log, LOG_HEADERS);
  if (!ss.getSheetByName(SHEETS.codes)) resetSheet_(ss, SHEETS.codes, CODE_HEADERS);
  PropertiesService.getScriptProperties().setProperty('LAST_HASH', 'GENESIS');

  [SHEETS.pool, SHEETS.draws, SHEETS.log].forEach(name => {
    const sh = ss.getSheetByName(name);
    sh.getProtections(SpreadsheetApp.ProtectionType.SHEET).forEach(p => p.remove());
    sh.protect().setDescription('Written by the lottery script — edits would break the audit').setWarningOnly(true);
  });

  log_('lottery_reset', {}, '', 'pool ' + s.min + '–' + s.max + ' (' + rows.length + ' numbers)');
  const def = ss.getSheetByName('Sheet1');
  if (def && def.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(def);
  ui.alert('Ready', rows.length + ' numbers (' + s.min + '–' + s.max + ') are in the pool. Now deploy the web app: Deploy → New deployment → Web app, Execute as: Me, Who has access: Anyone.', ui.ButtonSet.OK);
}

function openDraw() { setSetting_('open', true); log_('draw_opened_by_admin', {}, ''); SpreadsheetApp.getUi().alert('The draw is open. Customers can draw now.'); }
function closeDraw() { setSetting_('open', false); log_('draw_closed_by_admin', {}, ''); SpreadsheetApp.getUi().alert('The draw is closed. Customers will see a "closed" message.'); }

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

  const draws = sheet_(SHEETS.draws);
  const dn = draws.getLastRow() - 1;
  const d = dn > 0 ? draws.getRange(2, 1, dn, 9).getValues() : [];
  const seenNum = {}, seenPhone = {};
  d.forEach((r, i) => {
    const num = r[1], phone = String(r[3]);
    if (r[0] !== i + 1) issues.push('Draws row ' + (i + 2) + ': draw # is ' + r[0] + ', expected ' + (i + 1) + '.');
    if (num < s.min || num > s.max) issues.push('Number ' + num + ' is outside ' + s.min + '–' + s.max + '.');
    if (seenNum[num]) issues.push('Number ' + num + ' was given out twice (draws #' + seenNum[num] + ' and #' + r[0] + ').');
    if (seenPhone[phone]) issues.push('Phone ' + phone + ' drew twice (draws #' + seenPhone[phone] + ' and #' + r[0] + ').');
    seenNum[num] = r[0]; seenPhone[phone] = r[0];
  });

  const pool = sheet_(SHEETS.pool);
  const pv = pool.getRange(2, 1, pool.getLastRow() - 1, 3).getValues();
  let drawnInPool = 0;
  pv.forEach(r => {
    if (r[1] === 'drawn') { drawnInPool++; if (!seenNum[r[0]]) issues.push('Number ' + r[0] + ' is marked drawn in Pool but has no row in Draws.'); }
    else if (seenNum[r[0]]) issues.push('Number ' + r[0] + ' is in Draws but still marked available in Pool.');
  });

  const log = sheet_(SHEETS.log);
  const ln = log.getLastRow() - 1;
  let brokenAt = 0;
  if (ln > 0) {
    const lv = log.getRange(2, 1, ln, 9).getDisplayValues();
    let prev = 'GENESIS';
    for (let i = 0; i < lv.length; i++) {
      const h = chainHash_(prev, lv[i].slice(0, 8));
      if (h !== lv[i][8]) { brokenAt = i + 2; break; }
      prev = h;
    }
  }
  if (brokenAt) issues.push('Log row ' + brokenAt + ' (or one right before it) was edited, deleted or reordered after it was written.');
  const assignedInLog = ln > 0 ? log.getRange(2, 2, ln, 1).getValues().filter(r => r[0] === 'number_assigned').length : 0;
  if (assignedInLog !== d.length) issues.push('Log shows ' + assignedInLog + ' numbers assigned, but Draws has ' + d.length + ' rows.');

  log_('integrity_check_by_admin', {}, '', issues.length ? issues.length + ' issue(s)' : 'passed');
  const summary = d.length + ' numbers drawn, ' + (pv.length - drawnInPool) + ' left, ' + ln + ' log entries.\n\n';
  ui.alert(issues.length ? 'Integrity check: ' + issues.length + ' issue(s)' : 'Integrity check passed',
    summary + (issues.length ? issues.slice(0, 25).join('\n') : 'Every number was given out once, every phone drew once, the Pool matches the Draws list, and the log hash chain is unbroken.'),
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
function getOrCreate_(ss, name) { return ss.getSheetByName(name) || ss.insertSheet(name); }
function resetSheet_(ss, name, headers) {
  const sh = getOrCreate_(ss, name);
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
  return {
    title: String(map.title || 'Coupon Number Draw'),
    min: parseInt(map.min, 10) || 100,
    max: parseInt(map.max, 10) || 1300,
    open: map.open === undefined ? true : bool(map.open),
    requireCode: bool(map.require_code)
  };
}
function setSetting_(key, value) {
  const sh = sheet_(SHEETS.settings);
  const keys = sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues();
  const i = keys.findIndex(r => r[0] === key);
  if (i >= 0) sh.getRange(i + 2, 2).setValue(value);
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

/** Appends one log row. Must be called while holding the script lock. */
function log_(event, who, device, details, number) {
  who = who || {};
  const log = sheet_(SHEETS.log);
  const props = PropertiesService.getScriptProperties();
  const prev = props.getProperty('LAST_HASH') || 'GENESIS';
  // Store values as plain text so the hash re-check reads back exactly what was hashed
  const fields = [new Date().toISOString(), event, who.name || '', who.phone || '', who.code || '',
    number === undefined || number === '' ? '' : String(number), details || '', device || ''].map(String);
  const hash = chainHash_(prev, fields);
  const row = log.getLastRow() + 1;
  const range = log.getRange(row, 1, 1, 9);
  range.setNumberFormat('@');
  range.setValues([fields.concat([hash])]);
  props.setProperty('LAST_HASH', hash);
}

/** Logs from outside a draw (e.g. page opens), taking the lock briefly. */
function safeLog_(event, who, device, details) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return;
  try { log_(event, who, device, details); } catch (e) {} finally { lock.releaseLock(); }
}
