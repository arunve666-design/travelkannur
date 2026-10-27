/*
 * Coupon Number Draw — customer UI shared by index.html (live) and demo.html.
 *
 * Lottery.init({ mount, backend, storageKey }) where backend has:
 *   status()  -> {open, left, total, min, max, title, requireCode, usedTiles: [..]}
 *   visit(device)
 *   draw({tile, name, phone, code, device}) ->
 *     {status:'assigned'|'existing', tile, number, drawNo, left?}
 *     {status:'tile_taken', message, usedTiles}
 *     {status:'error'|'closed'|'empty', message}
 */
(function () {
  'use strict';

  function remote(url) {
    function call(body) {
      return fetch(url, { method: 'POST', body: JSON.stringify(body) }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
    }
    return {
      status: function () { return call({ action: 'status' }); },
      visit: function (device) { return call({ action: 'visit', device: device }); },
      draw: function (f) { var b = { action: 'draw' }; for (var k in f) b[k] = f[k]; return call(b); }
    };
  }

  var TEMPLATE =
    '<header>' +
      '<span class="eyebrow" data-l="range">Lottery · Numbers 100 – 1300</span>' +
      '<h1 data-l="title">Coupon Number Draw</h1>' +
      '<p class="muted">Pick any tile below. Behind it is a random number between <span data-l="min">100</span> and <span data-l="max">1300</span> that nobody has received yet. Each tile can be picked once, and each number can be won once.</p>' +
    '</header>' +
    '<section class="ticket" data-l="mine" hidden aria-live="polite">' +
      '<span class="t-label">Your result</span>' +
      '<div class="pair">' +
        '<div><span class="cap">Tile</span><span class="tileno" data-l="myTile"></span></div>' +
        '<span class="arrow" aria-hidden="true">→</span>' +
        '<div><span class="cap">Your number</span><span class="number won" data-l="myNum"></span></div>' +
      '</div>' +
      '<div class="t-foot"><span data-l="myDraw"></span><span>Take a screenshot to keep it</span></div>' +
    '</section>' +
    '<div class="err" data-l="err" hidden></div>' +
    '<div class="toolbar">' +
      '<span class="count" data-l="left">Loading tiles…</span>' +
      '<form class="find" data-l="find" novalidate>' +
        '<label class="sr" for="lFindInput">Find a tile</label>' +
        '<input id="lFindInput" data-l="findIn" type="number" inputmode="numeric" placeholder="Find tile">' +
        '<button class="btn-plain" type="submit">Go</button>' +
      '</form>' +
    '</div>' +
    '<div class="grid" data-l="grid" role="group" aria-label="Tiles"></div>' +
    '<div class="overlay" data-l="sheet" hidden>' +
      '<div class="sheet" role="dialog" aria-modal="true" aria-labelledby="lSheetTitle">' +
        '<div class="sheet-head"><h2 id="lSheetTitle" data-l="sheetTitle">Tile</h2>' +
          '<button class="x" type="button" data-l="close" aria-label="Close">×</button></div>' +
        '<div class="ticket" aria-live="polite">' +
          '<span class="t-label">Number behind this tile</span>' +
          '<div class="number idle" data-l="num">?</div>' +
        '</div>' +
        '<form data-l="form" novalidate>' +
          '<label for="lName">Your name<input id="lName" data-l="name" autocomplete="name" maxlength="80"></label>' +
          '<label for="lPhone">Phone number <span class="hint">Each phone number gets one pick</span>' +
            '<input id="lPhone" data-l="phone" type="tel" inputmode="tel" autocomplete="tel" maxlength="20"></label>' +
          '<label for="lCode" data-l="codeRow" hidden>Coupon code <span class="hint">Printed on your coupon, e.g. ABCD-2345</span>' +
            '<input id="lCode" data-l="code" autocapitalize="characters" autocomplete="off" maxlength="20"></label>' +
          '<div class="err" data-l="sheetErr" hidden></div>' +
          '<button class="btn" type="submit" data-l="go">Open tile</button>' +
        '</form>' +
        '<div class="done" data-l="done" hidden>' +
          '<p><strong data-l="doneMsg"></strong></p>' +
          '<button class="btn" type="button" data-l="doneBtn">Done</button>' +
        '</div>' +
      '</div>' +
    '</div>';

  function init(opts) {
    var root = opts.mount, backend = opts.backend, KEY = opts.storageKey || 'coupon-lottery-me';
    root.innerHTML = TEMPLATE;
    var $ = {};
    Array.prototype.forEach.call(root.querySelectorAll('[data-l]'), function (el) { $[el.getAttribute('data-l')] = el; });

    var MIN = 100, MAX = 1300, TOTAL = 1201, requireCode = false, isOpen = true, numbersLeft = null;
    var used = {}, tiles = {}, current = null, busy = false, loaded = false;
    var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var me = load();

    function load() { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { return null; } }
    function save() { try { if (me) localStorage.setItem(KEY, JSON.stringify(me)); else localStorage.removeItem(KEY); } catch (e) {} }
    function fmt(n) { return Number(n).toLocaleString('en-IN'); }
    function show(el, msg) { el.textContent = msg || ''; el.hidden = !msg; }
    function randInt(max) {
      if (window.crypto && crypto.getRandomValues) { var b = new Uint32Array(1); crypto.getRandomValues(b); return b[0] % max; }
      return Math.floor(Math.random() * max);
    }

    // ---------- board
    function buildGrid() {
      $.grid.textContent = '';
      tiles = {};
      var frag = document.createDocumentFragment();
      for (var v = MIN; v <= MAX; v++) {
        var b = document.createElement('button');
        b.type = 'button'; b.className = 'tile'; b.textContent = v; b.setAttribute('data-v', v);
        b.setAttribute('aria-label', 'Tile ' + v);
        tiles[v] = b; frag.appendChild(b);
      }
      $.grid.appendChild(frag);
    }
    function paint() {
      var usedCount = 0;
      for (var v = MIN; v <= MAX; v++) {
        var b = tiles[v], isUsed = !!used[v], mine = !!(me && me.tile === v);
        if (isUsed) usedCount++;
        b.disabled = isUsed || mine;
        b.classList.toggle('mine', mine);
        b.setAttribute('aria-label', 'Tile ' + v + (mine ? ', your pick' : isUsed ? ', already picked' : ''));
      }
      $.grid.classList.toggle('locked', !!me || !isOpen);
      if (loaded) {
        var tilesLeft = TOTAL - usedCount;
        $.left.innerHTML = '';
        $.left.appendChild(document.createTextNode(fmt(tilesLeft) + ' of ' + fmt(TOTAL) + ' tiles left'));
        var s = document.createElement('small'); s.textContent = 'updates live'; $.left.appendChild(s);
      }
      renderMine();
    }
    function renderMine() {
      if (!me) { $.mine.hidden = true; return; }
      $.mine.hidden = false;
      $.myTile.textContent = me.tile;
      $.myNum.textContent = me.number;
      $.myDraw.textContent = 'Draw #' + me.drawNo;
    }

    function applyStatus(s) {
      MIN = s.min; MAX = s.max; TOTAL = s.total; requireCode = !!s.requireCode; isOpen = !!s.open; numbersLeft = s.left;
      $.range.textContent = 'Lottery · Numbers ' + MIN + ' – ' + MAX;
      $.min.textContent = MIN; $.max.textContent = MAX;
      if (s.title) { $.title.textContent = s.title; document.title = s.title; }
      $.codeRow.hidden = !requireCode;
      if (!loaded || !tiles[MIN] || !tiles[MAX]) buildGrid();
      used = {};
      (s.usedTiles || []).forEach(function (v) { used[v] = true; });
      loaded = true;
      paint();
      if (me) show($.err, '');
      else if (!isOpen) show($.err, 'The draw is closed right now.');
      else if (numbersLeft === 0) show($.err, 'Every number has been given out. The draw is complete.');
      else show($.err, '');
      if (current && used[current] && !busy && $.done.hidden) {
        show($.sheetErr, 'Someone just picked tile ' + current + '. Please close this and choose another tile.');
        $.go.disabled = true;
      }
    }
    function refresh() {
      if (!backend) return Promise.resolve();
      return backend.status().then(applyStatus).catch(function () {
        if (!loaded) show($.err, 'Couldn\'t reach the draw. Check your connection and reload the page.');
      });
    }

    // ---------- pick sheet
    function openSheet(v) {
      if (me) { show($.err, 'You already picked tile ' + me.tile + '. Each person gets one pick.'); $.err.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' }); return; }
      if (!isOpen || used[v]) return;
      current = v;
      $.sheetTitle.textContent = 'Tile ' + v;
      $.num.textContent = '?'; $.num.className = 'number idle';
      $.go.textContent = 'Open tile ' + v; $.go.disabled = false;
      show($.sheetErr, ''); $.form.hidden = false; $.done.hidden = true;
      $.sheet.hidden = false;
      document.body.style.overflow = 'hidden';
      setTimeout(function () { ($.name.value ? $.go : $.name).focus(); }, 30);
    }
    function closeSheet() {
      if (busy) return;
      $.sheet.hidden = true; current = null;
      document.body.style.overflow = '';
    }

    function submit(ev) {
      ev.preventDefault();
      if (busy || current == null) return;
      show($.sheetErr, '');
      var name = $.name.value.trim(), phone = $.phone.value.trim(), code = $.code.value.trim();
      if (name.length < 2) return show($.sheetErr, 'Please enter your name.');
      if (phone.replace(/\D/g, '').length < 6) return show($.sheetErr, 'Please enter a valid phone number.');
      if (requireCode && !code) return show($.sheetErr, 'Please enter the code from your coupon.');

      busy = true; $.go.disabled = true; $.go.textContent = 'Shuffling…'; $.close.disabled = true;
      var n = $.num, tile = current, result, start = Date.now(), last = 0;
      n.className = 'number';
      function spin() {
        var el = Date.now() - start;
        if (result !== undefined && (el > 2200 || reduced)) return finish();
        if (!reduced && el - last > 40 + Math.pow(Math.min(el / 2200, 1), 2) * 140) { n.textContent = MIN + randInt(TOTAL); last = el; }
        requestAnimationFrame(spin);
      }
      function finish() {
        busy = false; $.close.disabled = false;
        $.go.textContent = 'Open tile ' + tile;
        if (result.status === 'assigned' || result.status === 'existing') {
          me = { tile: result.tile, number: result.number, drawNo: result.drawNo };
          save();
          used[result.tile] = true;
          n.textContent = result.number; n.className = 'number won';
          $.form.hidden = true; $.done.hidden = false;
          if (result.status === 'assigned') {
            $.sheetTitle.textContent = 'Tile ' + result.tile;
            $.doneMsg.textContent = 'Your number is ' + result.number + '. Tile ' + result.tile + ' and number ' + result.number + ' are now taken, so nobody else can get them.';
          } else {
            $.sheetTitle.textContent = 'You already picked';
            $.doneMsg.textContent = 'This phone number already picked tile ' + result.tile + ' and got number ' + result.number + '. Each person gets one pick.';
          }
          paint();
          $.doneBtn.focus();
        } else {
          n.textContent = '?'; n.className = 'number idle';
          show($.sheetErr, result.message || 'Something went wrong. Please try again.');
          if (result.status === 'tile_taken') {
            used = {}; (result.usedTiles || []).forEach(function (v) { used[v] = true; }); used[tile] = true;
            paint();
          } else {
            $.go.disabled = result.status === 'closed' || result.status === 'empty';
            if (result.status === 'closed' || result.status === 'empty') refresh();
          }
          if (result.status !== 'tile_taken' && !$.go.disabled) $.go.disabled = false;
        }
      }
      requestAnimationFrame(spin);
      backend.draw({ tile: tile, name: name, phone: phone, code: code, device: navigator.userAgent })
        .then(function (r) { result = r || { status: 'error' }; })
        .catch(function () { result = { status: 'error', message: 'Couldn\'t reach the draw. Check your connection and try again.' }; });
    }

    // ---------- events
    $.grid.addEventListener('click', function (e) {
      var b = e.target.closest('.tile');
      if (b) openSheet(parseInt(b.getAttribute('data-v'), 10));
    });
    $.form.addEventListener('submit', submit);
    $.close.addEventListener('click', closeSheet);
    $.doneBtn.addEventListener('click', function () { closeSheet(); $.mine.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' }); });
    $.sheet.addEventListener('click', function (e) { if (e.target === $.sheet) closeSheet(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !$.sheet.hidden) closeSheet(); });
    $.find.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = parseInt($.findIn.value, 10), b = tiles[v];
      if (!b) return;
      b.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
      b.classList.add('flash'); setTimeout(function () { b.classList.remove('flash'); }, 1600);
      if (!b.disabled) b.focus({ preventScroll: true });
    });

    // ---------- start
    buildGrid();
    renderMine();
    if (!backend) {
      $.left.textContent = '';
      show($.err, 'The draw isn\'t open yet. Please check back soon.');
      Array.prototype.forEach.call($.grid.children, function (b) { b.disabled = true; });
    } else {
      refresh();
      try { backend.visit(navigator.userAgent); } catch (e) {}
      setInterval(function () { if (!document.hidden && !busy) refresh(); }, 15000);
      document.addEventListener('visibilitychange', function () { if (!document.hidden && !busy) refresh(); });
    }

    return {
      refresh: refresh,
      resetMe: function () {
        me = null; save(); closeSheet();
        $.name.value = ''; $.phone.value = ''; $.code.value = '';
        show($.err, ''); paint();
      }
    };
  }

  window.Lottery = { init: init, remote: remote };
})();
