/**
 * Coupon Number Draw — public lottery on Google Sheets + Apps Script
 *
 * Customers see tiles 100–1300 on travelkannur.in/lottery/. They pick a tile,
 * enter name + phone, and the tile reveals a random hidden number (100–1300)
 * that nobody has received yet. After that:
 *   - the tile is gone for everyone (no one else can pick it), and
 *   - the hidden number is gone from the pool (no other tile can reveal it).
 * Each phone number gets one pick. Every action is written to the Log sheet
 * with a tamper-evident hash chain, so the organizer can audit everything.
 *
 * Sheets created by setup():
 *   Settings – draw open/closed, number range, coupon-code requirement
 *   Pool     – every value 100–1300: is the tile used? is the number given?
 *   Draws    – one row per pick (the official result list)
 *   Log      – every event: page opens, picks, repeats, rejections, errors
 *   Codes    – optional one-time coupon codes
 */

const SHEETS = { settings: 'Settings', pool: 'Pool', draws: 'Draws', log: 'Log', codes: 'Codes' };
const DRAW_HEADERS = ['Draw #', 'Tile picked', 'Number revealed', 'Name', 'Phone', 'Coupon code', 'Drawn at (local)', 'Drawn at (UTC)', 'Numbers left before draw', 'Draw ID'];
const LOG_HEADERS = ['Time (UTC)', 'Event', 'Name', 'Phone', 'Coupon code', 'Tile', 'Number', 'Details', 'Device', 'Hash'];
const POOL_HEADERS = ['Value', 'Tile', 'Hidden number', 'Tile used in draw #', 'Number given in draw #', 'Tile used at (UTC)'];
const CODE_HEADERS = ['Code', 'Status', 'Used by phone', 'Used at (UTC)', 'Number'];
const STATUS_CACHE_KEY = 'status-v2';

// ---------------------------------------------------------------- web app

/** The customer page is travelkannur.in/lottery/. Opening the script URL directly just points there. */
function doGet() {
  return HtmlService.createHtmlOutput(
    '<p style="font-family:sans-serif;padding:24px">This is the lottery backend. The draw is at ' +
    '<a href="https://travelkannur.in/lottery/" target="_top">travelkannur.in/lottery/</a>.</p>'
  ).setTitle('Lottery backend');
}

/**
 * JSON API used by travelkannur.in/lottery/.
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

/** Which tiles are gone, how many numbers are left, and whether the draw is open. Cached for 5 s. */
function getStatus() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get(STATUS_CACHE_KEY);
  if (hit) return JSON.parse(hit);
  const s = getSettings_();
  const rows = readPool_();
  const usedTiles = [];
  let left = 0;
  rows.forEach(r => {
    if (r[1] !== 'available') usedTiles.push(r[0]);
    if (r[2] === 'available') left++;
  });
  const out = {
    open: s.open, left: left, total: s.max - s.min + 1, min: s.min, max: s.max,
    title: s.title, requireCode: s.requireCode, usedTiles: usedTiles
  };
  try { cache.put(STATUS_CACHE_KEY, JSON.stringify(out), 5); } catch (e) {}
  return out;
}

function logVisit(device) {
  safeLog_('page_opened', {}, String(device || '').slice(0, 200));
}

/** A customer picked a tile. Reveals a random unused number behind it. */
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
    if (!s.open) { log_('rejected_draw_closed', who, device); return { status: 'closed', message: 'The draw is closed right now.' }; }
    if (isNaN(tile) || tile < s.min || tile > s.max) { log_('rejected_invalid_tile', who, device); return { status: 'error', message: 'That tile doesn\'t exist. Please choose a tile from the list.' }; }

    // One pick per phone number
    const draws = sheet_(SHEETS.draws);
    const dn = draws.getLastRow() - 1;
    if (dn > 0) {
      const prior = draws.getRange(2, 1, dn, 5).getValues().find(r => String(r[4]) === phone);
      if (prior) {
        log_('repeat_attempt_returned_existing', who, device, 'already has tile ' + prior[1], prior[2]);
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

    // The tile itself must still be free
    const ti = rows.findIndex(r => r[0] === tile);
    if (ti < 0 || rows[ti][1] !== 'available') {
      log_('rejected_tile_taken', who, device);
      return {
        status: 'tile_taken',
        message: 'Someone just picked tile ' + tile + '. Please choose another tile.',
        usedTiles: rows.filter(r => r[1] !== 'available').map(r => r[0])
      };
    }

    // Random hidden number nobody has received yet
    const available = [];
    rows.forEach((r, i) => { if (r[2] === 'available') available.push(i); });
    if (!available.length) { log_('rejected_pool_empty', who, device); return { status: 'empty', message: 'Every number has been given out. The draw is complete.' }; }

    const ni = available[secureRandomInt_(available.length)];
    const number = rows[ni][0];
    const now = new Date();
    const utc = now.toISOString();
    const local = Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
    const drawNo = dn + 1;
    const drawId = Utilities.getUuid();

    pool.getRange(ti + 2, 2).setValue('used');
    pool.getRange(ti + 2, 4).setValue(drawNo);
    pool.getRange(ti + 2, 6).setValue(utc);
    pool.getRange(ni + 2, 3).setValue('given');
    pool.getRange(ni + 2, 5).setValue(drawNo);
    draws.appendRow([drawNo, tile, number, name, "'" + phone, code, local, utc, available.length, drawId]);
    if (codeRow > 0) sheet_(SHEETS.codes).getRange(codeRow, 2, 1, 4).setValues([['used', "'" + phone, utc, number]]);
    log_('number_assigned', who, device, 'tile ' + tile + ' revealed ' + number + ', draw #' + drawNo + ', ' + available.length + ' numbers left before, id ' + drawId, number);
    SpreadsheetApp.flush();
    CacheService.getScriptCache().remove(STATUS_CACHE_KEY);
    return { status: 'assigned', tile: tile, number: number, drawNo: drawNo, left: available.length - 1 };
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
    const r = ui.alert('Reset the lottery?', 'This erases all ' + (existing.getLastRow() - 1) + ' draws and the log, and puts every tile and number back. This cannot be undone. Make a copy of the sheet first if you need the records.', ui.ButtonSet.YES_NO);
    if (r !== ui.Button.YES) return;
  }

  const settings = getOrCreate_(ss, SHEETS.settings);
  if (settings.getLastRow() < 2) {
    settings.clear();
    settings.getRange(1, 1, 6, 3).setValues([
      ['Setting', 'Value', 'What it does'],
      ['title', 'Coupon Number Draw', 'Name shown at the top of the customer page'],
      ['min', 100, 'Lowest tile / number'],
      ['max', 1300, 'Highest tile / number'],
      ['open', true, 'TRUE = customers can pick tiles, FALSE = draw is closed'],
      ['require_code', false, 'TRUE = customers must enter a one-time coupon code from the Codes sheet']
    ]);
    settings.setFrozenRows(1);
    settings.getRange('A1:C1').setFontWeight('bold');
    settings.autoResizeColumns(1, 3);
  }
  const s = getSettings_();

  const pool = resetSheet_(ss, SHEETS.pool, POOL_HEADERS);
  const rows = [];
  for (let n = s.min; n <= s.max; n++) rows.push([n, 'available', 'available', '', '', '']);
  pool.getRange(2, 1, rows.length, POOL_HEADERS.length).setValues(rows);

  resetSheet_(ss, SHEETS.draws, DRAW_HEADERS);
  resetSheet_(ss, SHEETS.log, LOG_HEADERS);
  if (!ss.getSheetByName(SHEETS.codes)) resetSheet_(ss, SHEETS.codes, CODE_HEADERS);
  PropertiesService.getScriptProperties().setProperty('LAST_HASH', 'GENESIS');
  CacheService.getScriptCache().remove(STATUS_CACHE_KEY);

  [SHEETS.pool, SHEETS.draws, SHEETS.log].forEach(name => {
    const sh = ss.getSheetByName(name);
    sh.getProtections(SpreadsheetApp.ProtectionType.SHEET).forEach(p => p.remove());
    sh.protect().setDescription('Written by the lottery script — edits would break the audit').setWarningOnly(true);
  });

  log_('lottery_reset', {}, '', 'tiles and numbers ' + s.min + '–' + s.max + ' (' + rows.length + ' each)');
  const def = ss.getSheetByName('Sheet1');
  if (def && def.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(def);
  ui.alert('Ready', rows.length + ' tiles and ' + rows.length + ' hidden numbers (' + s.min + '–' + s.max + ') are set. Now deploy: Deploy → New deployment → Web app, Execute as: Me, Who has access: Anyone.', ui.ButtonSet.OK);
}

function openDraw() { setSetting_('open', true); log_('draw_opened_by_admin', {}, ''); SpreadsheetApp.getUi().alert('The draw is open. Customers can pick tiles now.'); }
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
  const d = dn > 0 ? draws.getRange(2, 1, dn, 5).getValues() : [];
  const seenTile = {}, seenNum = {}, seenPhone = {};
  d.forEach((r, i) => {
    const no = r[0], tile = r[1], num = r[2], phone = String(r[4]);
    if (no !== i + 1) issues.push('Draws row ' + (i + 2) + ': draw # is ' + no + ', expected ' + (i + 1) + '.');
    if (tile < s.min || tile > s.max) issues.push('Tile ' + tile + ' is outside ' + s.min + '–' + s.max + '.');
    if (num < s.min || num > s.max) issues.push('Number ' + num + ' is outside ' + s.min + '–' + s.max + '.');
    if (seenTile[tile]) issues.push('Tile ' + tile + ' was picked twice (draws #' + seenTile[tile] + ' and #' + no + ').');
    if (seenNum[num]) issues.push('Number ' + num + ' was given out twice (draws #' + seenNum[num] + ' and #' + no + ').');
    if (seenPhone[phone]) issues.push('Phone ' + phone + ' picked twice (draws #' + seenPhone[phone] + ' and #' + no + ').');
    seenTile[tile] = no; seenNum[num] = no; seenPhone[phone] = no;
  });

  const pv = readPool_();
  let tilesUsed = 0, numsGiven = 0;
  pv.forEach(r => {
    const v = r[0];
    if (r[1] !== 'available') { tilesUsed++; if (!seenTile[v]) issues.push('Tile ' + v + ' is marked used in Pool but has no row in Draws.'); }
    else if (seenTile[v]) issues.push('Tile ' + v + ' is in Draws but still marked available in Pool.');
    if (r[2] !== 'available') { numsGiven++; if (!seenNum[v]) issues.push('Number ' + v + ' is marked given in Pool but has no row in Draws.'); }
    else if (seenNum[v]) issues.push('Number ' + v + ' is in Draws but still marked available in Pool.');
  });

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
  const assignedInLog = ln > 0 ? log.getRange(2, 2, ln, 1).getValues().filter(r => r[0] === 'number_assigned').length : 0;
  if (assignedInLog !== d.length) issues.push('Log shows ' + assignedInLog + ' picks, but Draws has ' + d.length + ' rows.');

  log_('integrity_check_by_admin', {}, '', issues.length ? issues.length + ' issue(s)' : 'passed');
  const summary = d.length + ' picks, ' + (pv.length - tilesUsed) + ' tiles left, ' + (pv.length - numsGiven) + ' numbers left, ' + ln + ' log entries.\n\n';
  ui.alert(issues.length ? 'Integrity check: ' + issues.length + ' issue(s)' : 'Integrity check passed',
    summary + (issues.length ? issues.slice(0, 25).join('\n') : 'Every tile was picked once, every number was given out once, every phone picked once, the Pool matches the Draws list, and the log hash chain is unbroken.'),
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
function readPool_() {
  const pool = sheet_(SHEETS.pool);
  const n = pool.getLastRow() - 1;
  return n > 0 ? pool.getRange(2, 1, n, 3).getValues() : [];
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

/** Appends one hash-chained log row. Must be called while holding the script lock. */
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

/** Logs from outside a draw (e.g. page opens), taking the lock briefly. */
function safeLog_(event, who, device, details) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return;
  try { log_(event, who, device, details); } catch (e) {} finally { lock.releaseLock(); }
}
