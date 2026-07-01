async function loadEpisodes() {
  const res = await fetch('data/episodes.json');
  const episodes = await res.json();
  const grid = document.getElementById('episode-grid');
  grid.innerHTML = '';

  episodes.forEach(ep => {
    const done = localStorage.getItem(`complete:${ep.id}`) === 'true';
    const card = document.createElement('a');
    card.className = 'episode-card';
    card.href = `episode.html?id=${ep.id}`;
    card.innerHTML = `
      ${done ? '<span class="badge-done">Done</span>' : ''}
      <h3>${ep.title_zh}</h3>
      <div class="en">${ep.title_en}</div>
      <div class="meta">${ep.era_zh} · ${ep.era_en}<br>${ep.level} · ~${ep.duration_min} min</div>
    `;
    grid.appendChild(card);
  });
}

loadEpisodes();
