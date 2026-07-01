# 如果国宝会说话 · English Learning Site

A small bilingual (Chinese/English) study site inspired by the CCTV documentary series
**如果国宝会说话** ("Every Treasure Tells a Story", also seen translated as
"If Treasures Could Talk"). It is built for English learners: each episode page shows
a transcript side by side, breaks down useful sentence patterns and vocabulary, and ends
with a short translation assignment.

## Copyright note (read this first)

The actual documentary is copyrighted by CCTV/its producers. This project does **not**
include real transcripts from the show. The two sample episodes in `data/` (`episode-01.json`,
`episode-02.json`) contain **original narration text** written for this project, based on
public-domain facts about the artifacts (陶鹰鼎 / the Pottery Eagle-Shaped Ding, and
越王勾践剑 / the Sword of Goujian) — not quotes from the broadcast.

If you own a licensed copy of the documentary, you can transcribe/translate short clips
yourself (for personal study use) and drop them into new files following the same JSON
schema described below.

## How it's built

Plain static site — no build step, no framework, no backend:

- `index.html` — episode list (home page)
- `episode.html` — transcript viewer (reads `?id=epXX` from the URL)
- `css/style.css` — styling
- `js/app.js` — renders the home page episode grid
- `js/episode.js` — renders transcript, patterns, vocabulary, and assignment for one episode
- `data/episodes.json` — index of all episodes (title, era, level, which file to load)
- `data/episode-XX.json` — one file per episode, containing:
  - `background` — short zh/en intro to the artifact
  - `transcript` — array of `{ zh, en, pattern_ref }` lines shown side by side
  - `sentence_patterns` — grammar/phrase explanations, each tied to a transcript line,
    with extra practice examples
  - `vocabulary` — key terms with pinyin, English gloss, and example sentences
  - `assignment` — Chinese sentences for the learner to translate, each with a hidden
    reference translation

Progress (completed episodes) and your own translation attempts are saved in the
browser's `localStorage` — nothing is sent to a server, so there is no backend to run.

## Running locally

Browsers block `fetch()` on `file://` pages, so serve the folder over HTTP:

```bash
cd chinese-english-learning
python3 -m http.server 8000
# open http://localhost:8000
```

Any static file server (or GitHub Pages / Netlify / Vercel static hosting) works too.

## Adding a new episode

1. Add an entry to `data/episodes.json`:
   ```json
   { "id": "ep03", "title_zh": "...", "title_en": "...", "era_zh": "...", "era_en": "...",
     "level": "Intermediate", "duration_min": 5, "file": "episode-03.json" }
   ```
2. Create `data/episode-03.json` following the schema used in `episode-01.json`.
3. Pick 3-5 transcript lines that showcase a genuinely useful English sentence pattern
   (e.g. inversion, cleft sentences, comparatives, participle clauses) and write them
   up under `sentence_patterns`, each with two extra practice examples.
4. Write 3-5 vocabulary entries and a short assignment with reference translations.

## Suggested study flow for a learner

1. Read the background, then go through the transcript once for meaning.
2. Read the "Sentence Patterns" section — these are the grammar payoff of the episode.
3. Review vocabulary.
4. Do the assignment: translate each Chinese sentence yourself *before* revealing the
   reference translation, then compare your wording against it.
5. Mark the episode complete — it'll show a "Done" badge on the home page.
