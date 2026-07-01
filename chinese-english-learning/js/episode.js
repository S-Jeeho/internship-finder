function getEpisodeId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id') || 'ep01';
}

async function loadEpisode() {
  const id = getEpisodeId();
  const indexRes = await fetch('data/episodes.json');
  const index = await indexRes.json();
  const meta = index.find(e => e.id === id) || index[0];

  const dataRes = await fetch(`data/${meta.file}`);
  const ep = await dataRes.json();

  renderHeader(ep, meta);
  renderBackground(ep);
  renderTranscript(ep);
  renderPatterns(ep);
  renderVocabulary(ep);
  renderAssignment(ep);
  renderCompleteToggle(ep);
}

function renderHeader(ep, meta) {
  document.title = `${ep.title_zh} / ${ep.title_en}`;
  document.getElementById('ep-title-zh').textContent = ep.title_zh;
  document.getElementById('ep-title-en').textContent = ep.title_en;
  document.getElementById('ep-meta').textContent =
    `${ep.era_zh} · ${ep.era_en} — ${ep.museum_zh} / ${ep.museum_en}`;
}

function renderBackground(ep) {
  document.getElementById('bg-zh').textContent = ep.background.zh;
  document.getElementById('bg-en').textContent = ep.background.en;
}

function renderTranscript(ep) {
  const container = document.getElementById('transcript');
  container.innerHTML = '';
  ep.transcript.forEach(line => {
    const row = document.createElement('div');
    row.className = 'transcript-row';
    row.innerHTML = `
      <div class="zh">${line.zh}</div>
      <div class="en">
        ${line.en}
        ${line.pattern_ref ? `<span class="pattern-tag" data-pattern="${line.pattern_ref}">pattern ↓</span>` : ''}
      </div>
    `;
    container.appendChild(row);
  });

  container.querySelectorAll('.pattern-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      const target = document.getElementById(`pattern-${tag.dataset.pattern}`);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });
}

function renderPatterns(ep) {
  const container = document.getElementById('patterns');
  container.innerHTML = '';
  ep.sentence_patterns.forEach(p => {
    const card = document.createElement('div');
    card.className = 'pattern-card';
    card.id = `pattern-${p.id}`;
    card.innerHTML = `
      <h4>${p.pattern}</h4>
      <p>${p.en_explanation}</p>
      <p style="color:#666">${p.zh_explanation}</p>
      <div class="quote">"${p.example_from_transcript}"</div>
      <strong>Try it yourself:</strong>
      <ul>${p.extra_examples.map(e => `<li>${e}</li>`).join('')}</ul>
    `;
    container.appendChild(card);
  });
}

function renderVocabulary(ep) {
  const tbody = document.getElementById('vocab-body');
  tbody.innerHTML = '';
  ep.vocabulary.forEach(v => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${v.term_zh}<br><span style="color:#999">${v.pinyin}</span></td>
      <td>${v.term_en} <em>(${v.pos})</em></td>
      <td>${v.example_zh}<br><span style="color:#666">${v.example_en}</span></td>
    `;
    tbody.appendChild(row);
  });
}

function renderAssignment(ep) {
  document.getElementById('assignment-instructions').innerHTML =
    `<p>${ep.assignment.instructions_en}</p><p style="color:#7c2222">${ep.assignment.instructions_zh}</p>`;

  const container = document.getElementById('assignment-list');
  container.innerHTML = '';

  ep.assignment.sentences.forEach((s, idx) => {
    const storageKey = `attempt:${ep.id}:${idx}`;
    const saved = localStorage.getItem(storageKey) || '';

    const item = document.createElement('div');
    item.className = 'assignment-item';
    item.innerHTML = `
      <div class="prompt-zh">${idx + 1}. ${s.zh}</div>
      <textarea placeholder="Type your English translation here...">${saved}</textarea>
      <div class="actions">
        <button class="btn secondary" data-action="reveal">Show reference translation</button>
        <span class="save-note">Your attempt is saved automatically in this browser.</span>
      </div>
      <div class="reference">${s.reference_en}</div>
    `;

    const textarea = item.querySelector('textarea');
    textarea.addEventListener('input', () => {
      localStorage.setItem(storageKey, textarea.value);
    });

    item.querySelector('[data-action="reveal"]').addEventListener('click', (e) => {
      item.querySelector('.reference').classList.toggle('visible');
      e.target.textContent = e.target.textContent.startsWith('Show')
        ? 'Hide reference translation'
        : 'Show reference translation';
    });

    container.appendChild(item);
  });
}

function renderCompleteToggle(ep) {
  const wrapper = document.getElementById('complete-toggle');
  const key = `complete:${ep.id}`;
  const done = localStorage.getItem(key) === 'true';
  wrapper.innerHTML = `
    <label class="complete-toggle">
      <input type="checkbox" id="complete-checkbox" ${done ? 'checked' : ''}>
      Mark this episode as completed
    </label>
  `;
  document.getElementById('complete-checkbox').addEventListener('change', (e) => {
    localStorage.setItem(key, e.target.checked ? 'true' : 'false');
  });
}

loadEpisode();
