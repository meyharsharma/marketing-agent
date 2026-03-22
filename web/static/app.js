/* ── Wizard state ─────────────────────────────────────────────── */
const state = {
  step: 0,
  platform: null,
  category: null,
  topic: null,
  topicData: null,  // Full content bank entry (for instant render)
  variant: null,    // "fact_a" or "fact_b" for did-you-know
  icp: 'solo-builder',
  jobId: null,
  pollTimer: null,
};

/* ── API helpers ─────────────────────────────────────────────── */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  return res.json();
}

/* ── Wizard navigation ───────────────────────────────────────── */
function getStepIds() {
  // Collect visible step panel IDs in order
  const panels = document.querySelectorAll('.wizard__panel');
  return Array.from(panels).map(p => p.id);
}

function showStep(n) {
  state.step = n;
  document.querySelectorAll('.wizard__panel').forEach((p, i) => {
    p.classList.toggle('wizard__panel--active', i === n);
  });
  document.querySelectorAll('.wizard__step-dot').forEach((d, i) => {
    d.classList.remove('wizard__step-dot--active', 'wizard__step-dot--done');
    if (i === n) d.classList.add('wizard__step-dot--active');
    else if (i < n) d.classList.add('wizard__step-dot--done');
  });
}

// Show/hide the variant step and its dot based on category
function updateVariantVisibility() {
  const variantPanel = document.getElementById('step-variant');
  const variantDot = document.getElementById('dot-variant');
  const needsVariant = state.category === 'did-you-know';

  if (variantPanel) variantPanel.style.display = needsVariant ? '' : 'none';
  if (variantDot) variantDot.style.display = needsVariant ? '' : 'none';
}

// The generate panel is always DOM index 4 (variant panel is always in DOM, just hidden)
function getGenerateStepIndex() {
  return 4;
}

function getVariantStepIndex() {
  return 3; // Always panel index 3 when visible
}

/* ── Step 1: Platforms ───────────────────────────────────────── */
async function loadPlatforms() {
  const platforms = await api('/api/platforms');
  const grid = document.getElementById('platform-grid');
  if (!grid) return;
  grid.innerHTML = '';

  // Only show platforms that support direct generation (cross-post-only platforms are excluded)
  const crosspostOnly = ['twitter'];
  const generatable = platforms.filter(p => !crosspostOnly.includes(p.id));

  generatable.forEach(p => {
    const card = document.createElement('div');
    card.className = 'select-card';
    card.innerHTML = `
      <div class="select-card__name">${p.name}</div>
      <div class="select-card__detail">Content platform</div>
    `;
    card.onclick = () => selectPlatform(p.id, card);
    grid.appendChild(card);
  });

  // Add "coming soon" placeholders
  ['Twitter/X', 'LinkedIn'].forEach(name => {
    const card = document.createElement('div');
    card.className = 'select-card select-card--disabled';
    card.innerHTML = `
      <div class="select-card__name">${name}</div>
      <div class="select-card__detail">${name === 'Twitter/X' ? 'Via cross-post' : 'Coming soon'}</div>
    `;
    grid.appendChild(card);
  });
}

function selectPlatform(id, card) {
  state.platform = id;
  document.querySelectorAll('#platform-grid .select-card').forEach(c =>
    c.classList.remove('select-card--selected')
  );
  card.classList.add('select-card--selected');
  setTimeout(() => {
    loadCategories(id);
    showStep(1);
  }, 200);
}

/* ── Step 2: Categories ──────────────────────────────────────── */
async function loadCategories(platform) {
  const categories = await api(`/api/categories/${platform}`);
  const grid = document.getElementById('category-grid');
  if (!grid) return;
  grid.innerHTML = '';

  categories.forEach(c => {
    const card = document.createElement('div');
    card.className = 'select-card';
    card.innerHTML = `
      <div class="select-card__name">${c.name}</div>
      <div class="select-card__detail">${truncate(c.description, 80)}</div>
      <div class="select-card__freq">${c.frequency} &middot; ${c.slot}</div>
    `;
    card.onclick = () => selectCategory(c.id, card);
    grid.appendChild(card);
  });
}

function selectCategory(id, card) {
  state.category = id;
  state.variant = null; // Reset variant when category changes
  document.querySelectorAll('#category-grid .select-card').forEach(c =>
    c.classList.remove('select-card--selected')
  );
  card.classList.add('select-card--selected');
  updateVariantVisibility();
  setTimeout(() => {
    loadTopics(state.platform, id);
    showStep(2);
  }, 200);
}

/* ── Step 3: Topics ──────────────────────────────────────────── */
async function loadTopics(platform, category) {
  const data = await api(`/api/topics/${platform}/${category}`);
  const grid = document.getElementById('topic-grid');
  const customWrap = document.getElementById('custom-topic-wrap');
  if (!grid) return;
  grid.innerHTML = '';

  // Topic label columns vary by category
  const labelMap = {
    'autopsy': { primary: 'bad_prompt', secondary: 'hook' },
    'did-you-know': { primary: 'fact', secondary: 'detail' },
    'prompt-drop': { primary: 'task', secondary: 'prompt_preview' },
    'prompt-pattern': { primary: 'pattern_name', secondary: 'core_insight' },
    'infographic': { primary: 'title', secondary: 'type' },
    'user-story': { primary: 'persona', secondary: 'problem' },
  };
  const labels = labelMap[category] || { primary: 'topic', secondary: '' };

  data.topics.forEach(t => {
    const card = document.createElement('div');
    card.className = 'topic-card';
    const primaryText = t[labels.primary] || JSON.stringify(t);
    const secondaryText = t[labels.secondary] || '';
    card.innerHTML = `
      <div class="topic-card__primary">${primaryText}</div>
      ${secondaryText ? `<div class="topic-card__secondary">${secondaryText}</div>` : ''}
    `;
    card.onclick = () => selectTopic(primaryText, card, t);
    grid.appendChild(card);
  });

  // Always show custom topic
  if (customWrap) customWrap.style.display = 'block';

  // Clear custom input selection state
  const customInput = document.getElementById('custom-topic-input');
  if (customInput) customInput.value = '';

  // Update the topic step button text based on whether variant step follows
  const topicNextBtn = document.getElementById('topic-next-btn');
  if (topicNextBtn) {
    topicNextBtn.textContent = category === 'did-you-know' ? 'Next' : 'Generate';
  }
}

function selectTopic(text, card, topicEntry) {
  state.topic = text;
  state.topicData = topicEntry || null;
  document.querySelectorAll('#topic-grid .topic-card').forEach(c =>
    c.classList.remove('topic-card--selected')
  );
  if (card) card.classList.add('topic-card--selected');

  // Clear custom input if selecting a preset
  const customInput = document.getElementById('custom-topic-input');
  if (customInput) customInput.value = '';

  enableTopicNextBtn();
}

function onCustomTopicInput(e) {
  const val = e.target.value.trim();
  if (val) {
    state.topic = val;
    state.topicData = null;  // Custom topic has no content bank data
    // Deselect preset cards
    document.querySelectorAll('#topic-grid .topic-card').forEach(c =>
      c.classList.remove('topic-card--selected')
    );
    enableTopicNextBtn();
  } else {
    state.topic = null;
    state.topicData = null;
  }
}

function enableTopicNextBtn() {
  const btn = document.getElementById('topic-next-btn');
  if (btn) btn.disabled = !state.topic;
}

// Called when the topic step's "Next" / "Generate" button is clicked
function onTopicNext() {
  if (!state.topic) return;
  if (state.category === 'did-you-know') {
    // Show variant step
    showStep(getVariantStepIndex());
  } else {
    startGeneration();
  }
}

/* ── Step 3b: Variant (did-you-know only) ────────────────────── */
function selectVariant(variant, card) {
  state.variant = variant;
  document.querySelectorAll('#variant-grid .select-card').forEach(c =>
    c.classList.remove('select-card--selected')
  );
  card.classList.add('select-card--selected');
  const btn = document.getElementById('variant-generate-btn');
  if (btn) btn.disabled = false;
}

function onVariantGenerate() {
  if (!state.variant) return;
  startGeneration();
}

/* ── Generation step ─────────────────────────────────────────── */
async function startGeneration() {
  if (!state.topic) return;

  showStep(getGenerateStepIndex());
  const progressEl = document.getElementById('progress-text');
  const progressPanel = document.getElementById('progress-panel');
  const inputPanel = document.getElementById('input-panel');
  if (progressPanel) progressPanel.style.display = 'block';
  if (inputPanel) inputPanel.style.display = 'none';

  const payload = {
    platform: state.platform,
    category: state.category,
    topic: state.topic,
    icp: state.icp,
  };
  if (state.variant) payload.variant = state.variant;
  if (state.topicData) payload.topic_data = state.topicData;

  const data = await api('/api/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  if (data.error) {
    if (progressEl) progressEl.textContent = 'Error: ' + data.error;
    return;
  }

  state.jobId = data.job_id;
  pollStatus();
}

function pollStatus() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    if (!state.jobId) return;
    const job = await api(`/api/generate/${state.jobId}/status`);
    const progressEl = document.getElementById('progress-text');

    if (job.status === 'generating') {
      if (progressEl) progressEl.textContent = job.progress || 'Working...';
    } else if (job.status === 'awaiting_input') {
      clearInterval(state.pollTimer);
      showAwaitingInput(job);
    } else if (job.status === 'complete') {
      clearInterval(state.pollTimer);
      window.location.href = `/preview/${job.output_path}`;
    } else if (job.status === 'error') {
      clearInterval(state.pollTimer);
      if (progressEl) progressEl.textContent = 'Error: ' + (job.error || 'Unknown error');
      document.querySelector('.spinner')?.remove();
    }
  }, 2000);
}

function showAwaitingInput(job) {
  const progressPanel = document.getElementById('progress-panel');
  const inputPanel = document.getElementById('input-panel');
  if (progressPanel) progressPanel.style.display = 'none';
  if (inputPanel) inputPanel.style.display = 'block';
}

async function submitOptimizedPrompt() {
  const textarea = document.getElementById('optimized-prompt');
  const val = textarea?.value.trim();
  if (!val) return;

  const progressPanel = document.getElementById('progress-panel');
  const inputPanel = document.getElementById('input-panel');
  if (progressPanel) progressPanel.style.display = 'block';
  if (inputPanel) inputPanel.style.display = 'none';

  const progressEl = document.getElementById('progress-text');
  if (progressEl) progressEl.textContent = 'Inserting optimized prompt...';

  await api(`/api/generate/${state.jobId}/continue`, {
    method: 'POST',
    body: JSON.stringify({ optimized_prompt: val }),
  });

  pollStatus();
}

/* ── Carousel viewer ─────────────────────────────────────────── */
function initCarousel() {
  const track = document.querySelector('.carousel__track');
  if (!track) return;

  const slides = track.querySelectorAll('.carousel__slide');
  const dots = document.querySelectorAll('.carousel__dot');
  let current = 0;

  function goTo(n) {
    current = Math.max(0, Math.min(n, slides.length - 1));
    slides[current].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
    dots.forEach((d, i) => d.classList.toggle('carousel__dot--active', i === current));
  }

  document.querySelector('.carousel__btn--prev')?.addEventListener('click', () => goTo(current - 1));
  document.querySelector('.carousel__btn--next')?.addEventListener('click', () => goTo(current + 1));
  dots.forEach((d, i) => d.addEventListener('click', () => goTo(i)));

  // Sync dots on scroll
  track.addEventListener('scroll', () => {
    const idx = Math.round(track.scrollLeft / track.offsetWidth);
    if (idx !== current) {
      current = idx;
      dots.forEach((d, i) => d.classList.toggle('carousel__dot--active', i === current));
    }
  });
}

/* ── Copy to clipboard ───────────────────────────────────────── */
function copyText(btnEl, text) {
  navigator.clipboard.writeText(text).then(() => {
    btnEl.textContent = 'Copied';
    btnEl.classList.add('copy-btn--copied');
    setTimeout(() => {
      btnEl.textContent = 'Copy';
      btnEl.classList.remove('copy-btn--copied');
    }, 1500);
  });
}

/* ── Collapsible sections ────────────────────────────────────── */
function toggleCollapsible(el) {
  el.closest('.collapsible').classList.toggle('collapsible--open');
}

/* ── Schedule form ───────────────────────────────────────────── */
async function submitSchedule(mode) {
  const mdPath = document.getElementById('schedule-md-path')?.value;
  const dateVal = document.getElementById('schedule-date')?.value;
  const timeVal = document.getElementById('schedule-time')?.value;
  const resultEl = document.getElementById('schedule-result');

  const payload = { markdown_path: mdPath, mode };
  if (mode === 'schedule') {
    if (!dateVal || !timeVal) {
      resultEl.textContent = 'Please select a date and time.';
      resultEl.className = 'schedule-result schedule-result--error';
      resultEl.style.display = 'block';
      return;
    }
    payload.datetime = `${dateVal} ${timeVal}`;
  }

  // Include selected slides if slide picker is present
  const picker = document.getElementById('slide-picker');
  if (picker) {
    const checked = picker.querySelectorAll('input[type="checkbox"]:checked');
    if (checked.length > 0) {
      payload.slides = Array.from(checked).map(cb => cb.value).join(',');
    }
  }

  // Disable buttons
  document.querySelectorAll('.schedule-actions .btn').forEach(b => b.disabled = true);

  const data = await api('/api/schedule', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  if (data.error) {
    resultEl.textContent = 'Error: ' + data.error;
    resultEl.className = 'schedule-result schedule-result--error';
  } else {
    resultEl.textContent = 'Scheduled successfully!';
    resultEl.className = 'schedule-result schedule-result--success';
  }
  resultEl.style.display = 'block';
  document.querySelectorAll('.schedule-actions .btn').forEach(b => b.disabled = false);
}

/* ── Utilities ───────────────────────────────────────────────── */
function truncate(str, n) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n) + '...' : str;
}

/* ── Init ────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Wizard page
  if (document.querySelector('.wizard')) {
    loadPlatforms();
    updateVariantVisibility();
    showStep(0);
  }
  // Preview page
  if (document.querySelector('.carousel')) {
    initCarousel();
  }
});
