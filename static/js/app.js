// ── State ──────────────────────────────────────────────────────────────────
const state = {
  spreadType: null,
  questions: [],
  deck: [],
  selectedCards: [],
  requiredCards: 0,
  positions: [],
};

const MONTHS = ["Januari","Februari","Mars","April","Maj","Juni",
                 "Juli","Augusti","September","Oktober","November","December"];

// ── Starfield ──────────────────────────────────────────────────────────────
function initStars() {
  const canvas = document.getElementById('stars-canvas');
  const ctx = canvas.getContext('2d');
  let stars = [];

  // Zodiac constellations: name + star positions (relative 0-1) + connections
  const ZODIACS = [
    { name: 'Aries', pos: [0.08,0.22], stars: [[0,0],[0.03,-0.04],[0.06,0],[0.09,0.04]], lines: [[0,1],[1,2],[2,3]] },
    { name: 'Taurus', pos: [0.18,0.55], stars: [[0,0],[0.04,0.03],[0.07,-0.01],[0.1,0.04],[0.06,0.07]], lines: [[0,1],[1,2],[2,3],[1,4]] },
    { name: 'Gemini', pos: [0.85,0.35], stars: [[0,0],[0.03,0.04],[0,0.08],[0.06,0],[0.09,0.04],[0.06,0.08]], lines: [[0,1],[1,2],[3,4],[4,5],[1,4]] },
    { name: 'Cancer', pos: [0.72,0.72], stars: [[0,0],[0.04,0.03],[0.02,0.07],[0.06,0.06]], lines: [[0,1],[1,2],[2,3],[3,1]] },
    { name: 'Leo', pos: [0.05,0.65], stars: [[0,0],[0.04,-0.03],[0.08,0],[0.1,0.05],[0.07,0.08],[0.03,0.07]], lines: [[0,1],[1,2],[2,3],[3,4],[4,5],[5,0]] },
    { name: 'Virgo', pos: [0.88,0.62], stars: [[0,0],[0.03,0.04],[0.01,0.08],[0.05,0.06],[0.08,0.03]], lines: [[0,1],[1,2],[1,3],[3,4]] },
    { name: 'Libra', pos: [0.25,0.82], stars: [[0,0],[0.05,0],[0.025,-0.05],[0.025,0.05]], lines: [[0,2],[2,1],[0,3],[3,1]] },
    { name: 'Scorpio', pos: [0.55,0.88], stars: [[0,0],[0.03,0.03],[0.06,0.02],[0.09,0.04],[0.07,0.07]], lines: [[0,1],[1,2],[2,3],[3,4]] },
    { name: 'Sagittarius', pos: [0.92,0.20], stars: [[0,0],[0.04,0.04],[0.07,0.01],[0.05,-0.04]], lines: [[0,1],[1,2],[2,3],[3,0]] },
    { name: 'Capricorn', pos: [0.35,0.12], stars: [[0,0],[0.04,-0.02],[0.08,0],[0.06,0.05],[0.02,0.05]], lines: [[0,1],[1,2],[2,3],[3,4],[4,0]] },
    { name: 'Aquarius', pos: [0.62,0.15], stars: [[0,0],[0.04,0.03],[0.08,0],[0.04,-0.03]], lines: [[0,1],[1,2],[0,3],[3,2]] },
    { name: 'Pisces', pos: [0.78,0.45], stars: [[0,0],[0.03,0.04],[0.06,0.01],[0.08,0.05],[0.04,-0.03]], lines: [[0,1],[1,2],[2,3],[0,4],[4,2]] },
  ];

  let constellations = [];

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    buildConstellations();
  }

  function buildConstellations() {
    const scale = Math.min(canvas.width, canvas.height) * 0.13;
    constellations = ZODIACS.map(z => ({
      name: z.name,
      stars: z.stars.map(([dx,dy]) => ({
        x: (z.pos[0] + dx) * canvas.width,
        y: (z.pos[1] + dy) * canvas.height,
      })),
      lines: z.lines,
    }));
  }

  function drawConstellations(t) {
    const pulse = 0.6 + 0.4 * Math.sin(t * 0.25);
    constellations.forEach((con, ci) => {
      const phase = t * 0.18 + ci * 0.5;
      const glow = 0.55 + 0.45 * Math.sin(phase);

      // Glowing connection lines
      ctx.save();
      ctx.strokeStyle = `rgba(200,140,255,${glow * 0.7})`;
      ctx.lineWidth = 1.2;
      ctx.shadowColor = 'rgba(180,100,255,0.8)';
      ctx.shadowBlur = 6;
      con.lines.forEach(([a, b]) => {
        ctx.beginPath();
        ctx.moveTo(con.stars[a].x, con.stars[a].y);
        ctx.lineTo(con.stars[b].x, con.stars[b].y);
        ctx.stroke();
      });
      ctx.restore();

      // Constellation stars — bright glowing dots
      con.stars.forEach((s, si) => {
        const starPhase = t * 0.4 + si * 1.1 + ci * 0.7;
        const sa = 0.7 + 0.3 * Math.sin(starPhase);
        // Glow ring
        const gr = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, 7);
        gr.addColorStop(0, `rgba(230,180,255,${sa})`);
        gr.addColorStop(0.4, `rgba(180,100,255,${sa * 0.5})`);
        gr.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.beginPath();
        ctx.arc(s.x, s.y, 7, 0, Math.PI * 2);
        ctx.fillStyle = gr;
        ctx.fill();
        // Core dot
        ctx.beginPath();
        ctx.arc(s.x, s.y, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(240, 210, 255, ${sa})`;
        ctx.fill();
      });

      // Zodiac name label
      const cx = con.stars.reduce((s,p) => s + p.x, 0) / con.stars.length;
      const cy = con.stars.reduce((s,p) => s + p.y, 0) / con.stars.length + 18;
      ctx.font = '10px "Crimson Text", serif';
      ctx.fillStyle = `rgba(200, 160, 255, ${glow * 0.75})`;
      ctx.textAlign = 'center';
      ctx.fillText(con.name, cx, cy);
    });
  }

  function createStars() {
    stars = [];
    for (let i = 0; i < 220; i++) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.4 + 0.2,
        alpha: Math.random(),
        speed: Math.random() * 0.005 + 0.002,
        phase: Math.random() * Math.PI * 2,
      });
    }
  }

  function drawMoon() {
    const mx = canvas.width * 0.82;
    const my = canvas.height * 0.13;
    const mr = 54;
    const t  = Date.now() / 4000;
    const pulse = 1 + 0.018 * Math.sin(t);

    // Yttre glöd
    for (let i = 5; i > 0; i--) {
      const gr = mr * pulse + i * 18;
      const ga = ctx.createRadialGradient(mx, my, mr * pulse, mx, my, gr);
      ga.addColorStop(0, `rgba(180,100,255,${0.07 * i / 5})`);
      ga.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.beginPath();
      ctx.arc(mx, my, gr, 0, Math.PI * 2);
      ctx.fillStyle = ga;
      ctx.fill();
    }

    // Månens kropp
    const mg = ctx.createRadialGradient(mx - mr*0.3, my - mr*0.3, mr*0.1, mx, my, mr * pulse);
    mg.addColorStop(0,   '#f5e6ff');
    mg.addColorStop(0.3, '#d4a0ff');
    mg.addColorStop(0.7, '#8b30cc');
    mg.addColorStop(1,   '#2a0060');
    ctx.beginPath();
    ctx.arc(mx, my, mr * pulse, 0, Math.PI * 2);
    ctx.fillStyle = mg;
    ctx.fill();

    // Halvmåne-skugga (crescent effect)
    ctx.beginPath();
    ctx.arc(mx + mr*0.3, my - mr*0.1, mr * 0.82 * pulse, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(7,0,15,0.72)';
    ctx.fill();

    // Kratrar / detaljer
    ctx.globalAlpha = 0.18;
    ctx.beginPath(); ctx.arc(mx - 12, my + 10, 8, 0, Math.PI*2); ctx.fillStyle='#fff'; ctx.fill();
    ctx.beginPath(); ctx.arc(mx - 22, my - 8,  5, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(mx - 8,  my + 25, 4, 0, Math.PI*2); ctx.fill();
    ctx.globalAlpha = 1;

    // Stjärnor runt månen
    const starAngles = [0.3,1.1,1.9,3.0,4.2,5.1];
    starAngles.forEach((a, i) => {
      const sd = mr * (1.7 + 0.4*(i%3));
      const sx = mx + sd * Math.cos(a + t*0.1);
      const sy = my + sd * Math.sin(a + t*0.1);
      const sa = 0.4 + 0.5 * Math.sin(t * (i+1) * 0.7);
      ctx.beginPath();
      ctx.arc(sx, sy, 1.5, 0, Math.PI*2);
      ctx.fillStyle = `rgba(220,180,255,${sa})`;
      ctx.fill();
    });
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const t = Date.now() / 1000;
    drawConstellations(t);
    drawMoon();
    stars.forEach(s => {
      const a = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(t * s.speed * 10 + s.phase));
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,240,255,${a * 0.9})`;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', () => { resize(); createStars(); });
  resize();
  createStars();
  buildConstellations();
  draw();
}

// ── Fetch deck ─────────────────────────────────────────────────────────────
async function loadDeck() {
  const res = await fetch('/api/cards');
  const cards = await res.json();
  // Shuffle
  for (let i = cards.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [cards[i], cards[j]] = [cards[j], cards[i]];
  }
  // Assign random reversal
  cards.forEach(c => { c.reversed = Math.random() < 0.3; });
  state.deck = cards;
}

// ── Section navigation ──────────────────────────────────────────────────────
function showSection(id) {
  ['intro-section','question-section','spread-section','reading-section'].forEach(s => {
    const el = document.getElementById(s);
    if (el) el.hidden = s !== id;
  });
}

// ── Spread selection ────────────────────────────────────────────────────────
document.querySelectorAll('.spread-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.spread-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.spreadType = btn.dataset.spread;
    setupQuestions(state.spreadType);
    showSection('question-section');
  });
});

function setupQuestions(type) {
  const container = document.getElementById('questions-container');
  container.innerHTML = '';

  const configs = {
    single: [{ label: 'DIN FRÅGA', placeholder: 'Vad behöver du klarhet kring just nu?' }],
    triple: [
      { label: 'FRÅGA 1', placeholder: 'Vad vill du utforska?' },
      { label: 'FRÅGA 2', placeholder: 'Vad behöver du se?' },
      { label: 'FRÅGA 3', placeholder: 'Vad söker du svar på?' },
    ],
    year: [],
  };

  const title = document.getElementById('question-section-title');
  if (type === 'year') {
    title.textContent = '🌙 Årsstjärnan';
    container.innerHTML = '<p style="text-align:center;color:var(--text-dim);font-style:italic;font-size:1.1rem;">Inget behöver sägas — universum känner ditt år.<br>Dra dina 13 kort och låt stjärnorna tala.</p>';
  } else {
    title.textContent = type === 'single' ? '⭐ Din Fråga' : '🌟 Tre Frågor';
    configs[type].forEach((cfg, i) => {
      const group = document.createElement('div');
      group.className = 'question-group';
      group.innerHTML = `
        <label>${cfg.label}</label>
        <textarea class="question-input" rows="2" placeholder="${cfg.placeholder}" data-index="${i}"></textarea>`;
      container.appendChild(group);
    });
  }
}

document.getElementById('to-spread-btn').addEventListener('click', () => {
  const inputs = document.querySelectorAll('.question-input');
  state.questions = [];
  if (state.spreadType !== 'year') {
    for (const inp of inputs) {
      if (!inp.value.trim()) {
        inp.focus();
        inp.style.borderColor = 'rgba(255,80,80,0.6)';
        setTimeout(() => inp.style.borderColor = '', 2000);
        return;
      }
      state.questions.push(inp.value.trim());
    }
  }
  buildSpread();
  showSection('spread-section');
});

document.getElementById('back-to-intro').addEventListener('click', () => {
  showSection('intro-section');
  resetState();
});

// ── Build spread UI ─────────────────────────────────────────────────────────
function buildSpread() {
  state.selectedCards = [];

  const configs = {
    single: { required: 3, positions: [
      {label:'Grunden'}, {label:'Kärnan'}, {label:'Vägen framåt'}
    ]},
    triple: { required: 9, positions: [
      {label:'Grunden',q:0},{label:'Kärnan',q:0},{label:'Vägen framåt',q:0},
      {label:'Grunden',q:1},{label:'Kärnan',q:1},{label:'Vägen framåt',q:1},
      {label:'Grunden',q:2},{label:'Kärnan',q:2},{label:'Vägen framåt',q:2},
    ]},
    year: { required: 13, positions: [
      ...MONTHS.map((m,i) => ({label:m,month:i})),
      {label:'Hela Året', center:true}
    ]},
  };

  const cfg = configs[state.spreadType];
  state.requiredCards = cfg.required;
  state.positions = cfg.positions;

  updateProgress();
  buildSpreadLayout();
  buildCardPool();
  document.getElementById('reveal-btn').disabled = true;
}

function updateProgress() {
  const el = document.getElementById('progress-text');
  const n = state.selectedCards.length;
  const total = state.requiredCards;
  if (n < total) {
    el.innerHTML = `Välj <span>${total - n}</span> kort till`;
  } else {
    el.innerHTML = `<span>Alla kort valda ✦</span>`;
    document.getElementById('reveal-btn').disabled = false;
  }
}

// ── Card pool ───────────────────────────────────────────────────────────────
function buildCardPool() {
  const pool = document.getElementById('card-pool');
  pool.innerHTML = '';

  // Show 26 random cards from deck (backs only)
  const shown = state.deck.slice(0, 26);
  shown.forEach((card, i) => {
    if (state.selectedCards.some(s => s.id === card.id)) return;
    const el = createPoolCard(card, i);
    pool.appendChild(el);
  });
}

function createPoolCard(card, i) {
  const el = document.createElement('div');
  el.className = 'card pool-card';
  el.dataset.id = card.id;
  el.style.animationDelay = `${i * 0.04}s`;
  el.innerHTML = `
    <div class="card-inner">
      <div class="card-back">
        <div class="card-back-inner">
          <span class="card-back-star">✦</span>
        </div>
      </div>
    </div>`;
  el.addEventListener('click', () => selectCard(card, el));
  return el;
}

// ── Select a card ───────────────────────────────────────────────────────────
function selectCard(card, poolEl) {
  if (state.selectedCards.length >= state.requiredCards) return;
  if (state.selectedCards.some(c => c.id === card.id)) return;

  state.selectedCards.push(card);
  poolEl.remove();

  // Refill pool if needed
  const usedIds = new Set(state.selectedCards.map(c => c.id));
  const available = state.deck.filter(c => !usedIds.has(c.id));
  if (available.length > 0 && state.selectedCards.length < state.requiredCards) {
    const next = available[Math.floor(Math.random() * available.length)];
    const newEl = createPoolCard(next, 0);
    document.getElementById('card-pool').appendChild(newEl);
  }

  placeCardInSpread(card, state.selectedCards.length - 1);
  updateProgress();
}

// ── Spread layout ────────────────────────────────────────────────────────────
function buildSpreadLayout() {
  const container = document.getElementById('spread-layout');
  container.innerHTML = '';

  if (state.spreadType === 'single') {
    buildSingleLayout(container);
  } else if (state.spreadType === 'triple') {
    buildTripleLayout(container);
  } else if (state.spreadType === 'year') {
    buildYearLayout(container);
  }
}

function buildSingleLayout(container) {
  const row = document.createElement('div');
  row.className = 'spread-single';
  state.positions.forEach((pos, i) => {
    const slot = document.createElement('div');
    slot.className = 'spread-card-slot';
    slot.innerHTML = `
      <div class="slot-label">${pos.label}</div>
      <div class="slot-placeholder" id="slot-${i}">✦</div>`;
    row.appendChild(slot);
  });
  container.appendChild(row);
}

function buildTripleLayout(container) {
  const wrap = document.createElement('div');
  wrap.className = 'spread-triple';
  for (let q = 0; q < 3; q++) {
    const group = document.createElement('div');
    group.className = 'question-group-spread';
    group.innerHTML = `<div class="question-group-label">${state.questions[q] || 'Fråga ' + (q+1)}</div>`;
    const row = document.createElement('div');
    row.className = 'question-cards-row';
    ['Grunden','Kärnan','Vägen framåt'].forEach((lbl, j) => {
      const i = q * 3 + j;
      const slot = document.createElement('div');
      slot.className = 'spread-card-slot';
      slot.innerHTML = `
        <div class="slot-label">${lbl}</div>
        <div class="slot-placeholder" id="slot-${i}">✦</div>`;
      row.appendChild(slot);
    });
    group.appendChild(row);
    wrap.appendChild(group);
  }
  container.appendChild(wrap);
}

function buildYearLayout(container) {
  const wrap = document.createElement('div');
  wrap.className = 'spread-year';

  // 12 month cards in a circle
  const cx = 50, cy = 50, r = 38;
  MONTHS.forEach((month, i) => {
    const angle = (i / 12) * 2 * Math.PI - Math.PI / 2;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    const slot = document.createElement('div');
    slot.className = 'year-card-slot';
    slot.style.left = `${x}%`;
    slot.style.top = `${y}%`;
    slot.style.transform = 'translate(-50%, -50%)';
    slot.innerHTML = `
      <div class="year-slot-label">${month}</div>
      <div class="slot-placeholder year-ring-card" id="slot-${i}">✦</div>`;
    wrap.appendChild(slot);
  });

  // Center card
  const center = document.createElement('div');
  center.className = 'year-center-slot';
  center.innerHTML = `
    <div class="slot-label" style="color:var(--gold);font-size:0.75rem;">HELA ÅRET</div>
    <div class="slot-placeholder" id="slot-12" style="width:100px;height:168px;">✦</div>`;
  wrap.appendChild(center);

  container.appendChild(wrap);
}

// ── Place selected card in spread ────────────────────────────────────────────
function placeCardInSpread(card, index) {
  const slotEl = document.getElementById(`slot-${index}`);
  if (!slotEl) return;

  const cardEl = document.createElement('div');
  const isYear = state.spreadType === 'year';
  const isCenter = index === 12;
  cardEl.className = 'card' + (isYear && !isCenter ? ' year-ring-card' : '') + (card.reversed ? ' reversed' : '');

  const imgSrc = `/static/images/cards/${card.image}`;
  cardEl.innerHTML = `
    <div class="card-inner">
      <div class="card-back">
        <div class="card-back-inner"><span class="card-back-star">✦</span></div>
      </div>
      <div class="card-front">
        <img src="${imgSrc}" alt="${card.name_sv}" onload="this.classList.add('loaded')">
        <div class="card-label">
          ${card.name_sv}
          ${card.reversed ? '<span class="reversed-badge">omvänd</span>' : ''}
        </div>
      </div>
    </div>`;

  slotEl.replaceWith(cardEl);

  // Flip after a short delay
  setTimeout(() => cardEl.classList.add('flipped'), 300);
}

// ── Reveal reading ───────────────────────────────────────────────────────────
document.getElementById('reveal-btn').addEventListener('click', async () => {
  buildDrawnSummary();
  showSection('reading-section');
  await streamReading();
});

function buildDrawnSummary() {
  const container = document.getElementById('drawn-cards-summary');
  container.innerHTML = '';
  state.selectedCards.forEach(c => {
    const chip = document.createElement('div');
    chip.className = 'drawn-card-chip' + (c.reversed ? ' reversed' : '');
    chip.textContent = c.name_sv + (c.reversed ? ' ↓' : '');
    container.appendChild(chip);
  });
}

async function streamReading() {
  const textEl = document.getElementById('reading-text');
  textEl.innerHTML = '<span class="cursor"></span>';

  const body = {
    spread_type: state.spreadType,
    questions: state.questions,
    cards: state.selectedCards.map((c, i) => ({
      id: c.id,
      name: c.name,
      name_sv: c.name_sv,
      reversed: c.reversed,
      position_label: state.positions[i]?.label || '',
    })),
  };

  try {
    const res = await fetch('/api/reading', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') {
          textEl.innerHTML = formatReadingText(fullText);
          initFollowup(fullText);
          return;
        }
        try {
          const obj = JSON.parse(raw);
          if (obj.text) {
            fullText += obj.text;
            textEl.innerHTML = escapeHtml(fullText) + '<span class="cursor"></span>';
            textEl.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }
        } catch {}
      }
    }
  } catch (e) {
    textEl.innerHTML = '<em style="color:#ff8080">Något gick fel. Försök igen.</em>';
    console.error(e);
  }
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Följdfrågor ─────────────────────────────────────────────────────────────
const MAX_FOLLOWUPS = 10;
let followupCount = 0;
let followupHistory = [];  // [{role:'user'|'assistant', content:string}]

function initFollowup(initialReading) {
  followupCount = 0;
  followupHistory = [{ role: 'assistant', content: initialReading }];
  updateFollowupCounter();
  document.getElementById('followup-history').innerHTML = '';
  document.getElementById('followup-done').hidden = true;
  document.getElementById('followup-input-wrap').hidden = false;
  document.getElementById('followup-input').value = '';
}

function updateFollowupCounter() {
  const remaining = MAX_FOLLOWUPS - followupCount;
  document.getElementById('followup-remaining').textContent = remaining;
}

document.getElementById('followup-btn').addEventListener('click', sendFollowup);
document.getElementById('followup-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendFollowup(); }
});

async function sendFollowup() {
  const input = document.getElementById('followup-input');
  const question = input.value.trim();
  if (!question) return;
  if (followupCount >= MAX_FOLLOWUPS) return;

  followupCount++;
  updateFollowupCounter();
  input.value = '';
  input.disabled = true;
  document.getElementById('followup-btn').disabled = true;

  // Lägg till frågan i historiken
  followupHistory.push({ role: 'user', content: question });

  const history = document.getElementById('followup-history');

  // Visa frågan
  const qEl = document.createElement('div');
  qEl.className = 'followup-q';
  qEl.textContent = question;
  history.appendChild(qEl);

  // Skapa svar-element med cursor
  const aEl = document.createElement('div');
  aEl.className = 'followup-a';
  aEl.innerHTML = '<span class="cursor"></span>';
  history.appendChild(aEl);
  aEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

  let fullAnswer = '';

  try {
    const res = await fetch('/api/followup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ history: followupHistory, question }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') {
          aEl.innerHTML = formatReadingText(fullAnswer);
          followupHistory.push({ role: 'assistant', content: fullAnswer });
          break;
        }
        try {
          const obj = JSON.parse(raw);
          if (obj.text) {
            fullAnswer += obj.text;
            aEl.innerHTML = escapeHtml(fullAnswer) + '<span class="cursor"></span>';
          }
        } catch {}
      }
    }
  } catch (e) {
    aEl.innerHTML = '<em style="color:#ff8080">Något gick fel. Försök igen.</em>';
  }

  // Återaktivera input om det finns fler frågor kvar
  if (followupCount >= MAX_FOLLOWUPS) {
    document.getElementById('followup-input-wrap').hidden = true;
    document.getElementById('followup-done').hidden = false;
  } else {
    input.disabled = false;
    document.getElementById('followup-btn').disabled = false;
    input.focus();
  }
}

function formatReadingText(text) {
  const parts = text.split(/(✦ Råd:[^\n]*(?:\n[^\n]+)*)/g);
  let html = '';
  parts.forEach(part => {
    if (part.startsWith('✦ Råd:')) {
      html += `<span class="reading-advice">${escapeHtml(part)}</span>`;
    } else {
      html += escapeHtml(part).replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    }
  });
  return `<p>${html}</p>`;
}

// ── Följdfråga med kort ─────────────────────────────────────────────────────
let cardFollowupDrawnCard = null;
let cardFollowupReady = false;

document.getElementById('card-followup-btn').addEventListener('click', () => {
  const panel = document.getElementById('card-followup-panel');
  panel.hidden = !panel.hidden;
  if (!panel.hidden) {
    resetCardFollowup();
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
});

function resetCardFollowup() {
  cardFollowupDrawnCard = null;
  cardFollowupReady = false;
  document.getElementById('card-followup-input').value = '';
  document.getElementById('card-followup-submit').disabled = true;
  document.getElementById('card-followup-draw-hint') &&
    (document.querySelector('.card-followup-draw-hint').textContent = 'Klicka på kortet för att dra det');

  // Återställ kort till baksida
  const cardEl = document.getElementById('card-followup-card');
  cardEl.className = 'card pool-card';
  cardEl.innerHTML = `
    <div class="card-inner">
      <div class="card-back">
        <div class="card-back-inner"><span class="card-back-star">✦</span></div>
      </div>
    </div>`;
  cardEl.onclick = drawCardFollowup;
}

function drawCardFollowup() {
  if (cardFollowupDrawnCard) return;

  // Plocka ett slumpmässigt kort som inte redan dragits
  const usedIds = new Set(state.selectedCards.map(c => c.id));
  const available = state.deck.filter(c => !usedIds.has(c.id));
  if (available.length === 0) return;

  const card = available[Math.floor(Math.random() * available.length)];
  card.reversed = Math.random() < 0.3;
  cardFollowupDrawnCard = card;

  const cardEl = document.getElementById('card-followup-card');
  cardEl.className = 'card' + (card.reversed ? ' reversed' : '');
  cardEl.innerHTML = `
    <div class="card-inner">
      <div class="card-back">
        <div class="card-back-inner"><span class="card-back-star">✦</span></div>
      </div>
      <div class="card-front">
        <img src="/static/images/cards/${card.image}" alt="${card.name_sv}" onload="this.classList.add('loaded')">
        <div class="card-label">
          ${card.name_sv}
          ${card.reversed ? '<span class="reversed-badge">omvänd</span>' : ''}
        </div>
      </div>
    </div>`;
  cardEl.onclick = null;

  setTimeout(() => cardEl.classList.add('flipped'), 100);

  document.querySelector('.card-followup-draw-hint').textContent =
    card.name_sv + (card.reversed ? ' (omvänd)' : '');

  checkCardFollowupReady();
}

document.getElementById('card-followup-input').addEventListener('input', checkCardFollowupReady);

function checkCardFollowupReady() {
  const q = document.getElementById('card-followup-input').value.trim();
  const ready = !!cardFollowupDrawnCard && q.length > 0;
  document.getElementById('card-followup-submit').disabled = !ready;
}

document.getElementById('card-followup-submit').addEventListener('click', async () => {
  const q = document.getElementById('card-followup-input').value.trim();
  if (!q || !cardFollowupDrawnCard) return;

  const card = cardFollowupDrawnCard;
  const cardDesc = `${card.name_sv}${card.reversed ? ' [OMVÄND]' : ''}`;
  const fullQuestion = `Följdfråga: "${q}"\n\nKortet som dragits för den här frågan: ${cardDesc}\n\nTolka kortet i relation till min fråga och det tidigare svaret.`;

  // Dölj panel
  document.getElementById('card-followup-panel').hidden = true;

  // Lägg in i följdfrågehistoriken
  followupCount++;
  updateFollowupCounter();
  followupHistory.push({ role: 'user', content: fullQuestion });

  const history = document.getElementById('followup-history');

  const qEl = document.createElement('div');
  qEl.className = 'followup-q';
  qEl.innerHTML = `${escapeHtml(q)} <em style="color:var(--gold);font-size:0.9em">· ${escapeHtml(cardDesc)}</em>`;
  history.appendChild(qEl);

  const aEl = document.createElement('div');
  aEl.className = 'followup-a';
  aEl.innerHTML = '<span class="cursor"></span>';
  history.appendChild(aEl);
  aEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

  let fullAnswer = '';
  try {
    const res = await fetch('/api/followup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ history: followupHistory, question: fullQuestion }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') {
          aEl.innerHTML = formatReadingText(fullAnswer);
          followupHistory.push({ role: 'assistant', content: fullAnswer });
          break;
        }
        try {
          const obj = JSON.parse(raw);
          if (obj.text) { fullAnswer += obj.text; aEl.innerHTML = escapeHtml(fullAnswer) + '<span class="cursor"></span>'; }
        } catch {}
      }
    }
  } catch {
    aEl.innerHTML = '<em style="color:#ff8080">Något gick fel.</em>';
  }

  if (followupCount >= MAX_FOLLOWUPS) {
    document.getElementById('followup-input-wrap').hidden = true;
    document.getElementById('followup-done').hidden = false;
  }
});

// ── New reading button ───────────────────────────────────────────────────────
document.getElementById('new-reading-btn').addEventListener('click', () => {
  resetState();
  showSection('intro-section');
});

function resetState() {
  state.spreadType = null;
  state.questions = [];
  state.selectedCards = [];
  document.querySelectorAll('.spread-btn').forEach(b => b.classList.remove('active'));
}

// ── Init ─────────────────────────────────────────────────────────────────────
initStars();
loadDeck();
