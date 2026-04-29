# Science Communicator Agent — Project Documentation

A multi-agent pipeline that turns a one-line topic ("Show why the area of a
circle is πr²") into a fully narrated 3Blue1Brown-style explainer video.

This document walks through everything that has been built so far: the
architecture, every module, the data model, the generation flow, and the
quality gates.

---

## 1. What the system does

**Input:** a natural-language topic.

**Output:** a single `final.mp4` — a 60–150-second animated explainer with
synchronized Gemini-TTS narration, optionally with background music.

**Stack:**

| Layer              | Tool                                                     |
| ------------------ | -------------------------------------------------------- |
| Animation engine   | [Manim Community](https://www.manim.community/) v0.20+   |
| Narration          | Gemini 2.5 TTS (native), via a custom `manim-voiceover` adapter |
| Scripting / agents | Google `google-genai` SDK (Gemini 2.5 Pro)               |
| Video editing      | `ffmpeg` (concat, mux), `moviepy`                        |
| CLI                | `typer` + `rich`                                         |

There are **two execution paths** in `scripts/generate.py`:

1. **Multi-agent pipeline (default).** Plan → render N scenes in parallel →
   stitch → QA → auto-patch loop. This is the core of the project.
2. **`--simple` legacy path.** A single Gemini call generates one Manim file,
   renders it with up to 2 self-repair attempts. Kept for quick iteration.

---

## 2. High-level architecture

```
                    ┌──────────────────────────┐
   topic ────────► │  Master Planner (Gemini)  │  → ScenePlan (JSON)
                    └────────────┬─────────────┘
                                 │
                  ┌──────────────┼─────────────────────────────┐
                  │              │                             │
            ┌─────▼─────┐  ┌─────▼─────┐                ┌──────▼──────┐
            │ Worker 01 │  │ Worker 02 │      …         │  Worker NN  │
            │ (Gemini)  │  │           │                │             │
            └─────┬─────┘  └─────┬─────┘                └──────┬──────┘
                  │              │                             │
              manim render   manim render                  manim render
                  │              │                             │
            ┌─────▼─────┐  ┌─────▼─────┐                ┌──────▼──────┐
            │  Judge    │  │  Judge    │      …         │   Judge     │
            │ (vision)  │  │           │                │             │
            └─────┬─────┘  └─────┬─────┘                └──────┬──────┘
                  │              │                             │
                  └──────────────┼─────────────────────────────┘
                                 │
                       ┌─────────▼─────────┐
                       │   ffmpeg concat   │  → final.mp4 (v1)
                       └─────────┬─────────┘
                                 │
                  ┌──────────────▼──────────────┐
                  │ Master QA  +  Continuity    │  ← deterministic checks +
                  │  (Gemini, multimodal)       │     vision on adjacent boundaries
                  └──────────────┬──────────────┘
                                 │
                       (issues found?)
                          │           │
                        yes           no  → done
                          │
            ┌─────────────▼─────────────┐
            │ Patch failing scenes      │
            │ (re-run Worker → Judge)   │
            └─────────────┬─────────────┘
                          │
                          └─► re-stitch → loop (up to N patch passes)
```

Five LLM-driven roles, each implemented as a plain async function around
Gemini structured output:

| Role          | Module                       | Model used         | Output           |
| ------------- | ---------------------------- | ------------------ | ---------------- |
| Planner       | `src/agents/master.py`       | gemini-2.5-pro     | `ScenePlan`      |
| Worker        | `src/agents/scene_worker.py` | gemini-2.5-pro     | Python file      |
| Judge         | `src/agents/judge.py`        | gemini-2.5-pro (multimodal) | `JudgeReport` |
| Continuity    | `src/agents/continuity.py`   | gemini-2.5-pro (multimodal) | issue list   |
| Master QA     | `src/agents/master.py`       | gemini-2.5-pro     | `QAReport`       |

ADK is referenced conceptually, but in practice we call `google-genai` directly
with `response_schema=` for structured output — that gave us the most reliable
JSON without needing ADK's tool-calling machinery.

---

## 3. Repository layout

```
science-communicator-agent/
├── README.md                # quick-start
├── DOCUMENTATION.md         # ← this file
├── requirements.txt
├── .env.example             # GOOGLE_API_KEY, ELEVENLABS_API_KEY, etc.
├── .gitignore
├── scripts/
│   └── generate.py          # Typer CLI entry point
├── src/
│   ├── gemini_agent.py      # legacy single-shot generator + base SYSTEM_PROMPT
│   ├── compositor.py        # moviepy: mux narration onto video
│   ├── music.py             # ffmpeg: duck/loop a music bed under the mix
│   ├── narrator.py          # standalone TTS helpers (edge-tts / gTTS / ElevenLabs)
│   └── agents/
│       ├── pipeline.py      # top-level orchestrator (asyncio)
│       ├── master.py        # Planner + Master QA + deterministic checks
│       ├── scene_runner.py  # dispatch simple vs complex (sub-scene) rendering
│       ├── scene_worker.py  # generate / render / judge / repair loop per scene
│       ├── judge.py         # vision-based per-scene judge
│       ├── continuity.py    # cross-scene boundary check
│       ├── prompts.py       # all system prompts in one place
│       ├── schemas.py       # dataclasses + Gemini response_schema dicts
│       ├── tts.py           # GeminiTTSService (manim-voiceover adapter)
│       └── tools.py         # subprocess wrappers: manim, ffmpeg, ffprobe
└── scenes/
    ├── example.py                                # SquareToCircle / EulerIdentity demo
    ├── <legacy hand-written or simple-mode files>
    └── <run_id>/                                 # per-run worker outputs
        ├── <slug>.py
        ├── <slug>__a_<sub_slug>.py
        └── ...
```

`output/<run_id>/` (gitignored) holds the artifacts of each run:

```
output/<run_id>/
├── plan.json                     # the ScenePlan from the planner
├── qa.json                       # the latest QAReport
├── continuity.json               # cross-scene boundary issues
├── patch_log.json                # what was re-rendered and why
├── scene_<id>.mp4                # one stable mp4 per scene (concat input)
├── frames_<id>_attempt<N>/       # frames sampled for the judge
├── continuity_frames/            # last/first frames of adjacent scenes
├── judge_<id>_attempt<N>.json    # raw judge reports per attempt
└── final.mp4                     # ← the deliverable
```

---

## 4. The data model (`src/agents/schemas.py`)

Every agent boundary is a dataclass with a matching JSON schema. The schemas
are passed to Gemini as `response_schema=` so we get back valid JSON.

### `ScenePlan` — the planner's output

```
ScenePlan
├── topic, title, total_target_seconds, voice
├── scenes: list[ScenePlanItem]
│   ├── id ("01", "02", …)
│   ├── slug ("concentric_rings")
│   ├── description, target_seconds, key_visuals, correctness_checks
│   ├── complexity: "simple" | "complex"
│   ├── beats: list[NarrationBeat]      ← when complexity == "simple"
│   └── sub_scenes: list[SubScene]      ← when complexity == "complex"
│       └── (each SubScene has its own beats, target_seconds, etc.)
└── shared_objects: list[SharedObject]  ← cross-scene continuity contract
    ├── name, color, label, spec
    └── appears_in: ["03", "04", …]
```

A `NarrationBeat` is `(text, animation_hint)` — the `text` is verbatim TTS
input; `animation_hint` is a free-text instruction the worker uses when
generating the Manim code.

### `SharedObject` — the continuity contract

The single most important structural decision in the plan. Whenever a visual
element appears in two or more scenes (e.g. "the unrolled triangle" that gets
introduced in scene 03 and re-used in scene 04), the planner pins it down with
explicit vertices, color, and label. Workers and the judge both receive this
spec, and the continuity agent later compares boundary frames against it.

### `SceneResult` — the worker's output for one scene

`(id, scene_class, scene_file, video_path, duration_seconds, attempts,
success, last_error, last_judge: JudgeReport)`.

### `JudgeReport` — per-scene visual gate

```
JudgeReport
├── passed: bool
├── overall_assessment: str
└── issues: list[JudgeIssue]
    ├── kind: "text_overlap" | "geometric_error" | "narration_mismatch"
    │       | "off_screen" | "wrong_object_count" | "duration_mismatch"
    │       | "color_legibility" | "continuity_*"
    ├── severity: "low" | "medium" | "high"
    ├── where, description
    └── fix_hint  ← actionable, fed back into worker repair
```

### `QAReport` — master/global gate

`(overall_ok: bool, issues: list[QAIssue], notes: str)` — issues here are
cross-scene concerns (pacing, narrative flow, total-duration drift).

---

## 5. End-to-end generation flow

Driver: `src/agents/pipeline.py::run`. All phases are `asyncio` and
`asyncio.to_thread` wraps every blocking SDK / subprocess call.

### Phase 1 — Plan

`master.plan_video(topic)` → `ScenePlan`.

- The planner is told to choose a 60–150s total, decompose into 3–7 scenes,
  decide simple-vs-complex per scene, attach `correctness_checks`, pick a
  Gemini TTS voice, and **populate `shared_objects`** for any element that
  spans scenes.
- `_validate_plan` enforces invariants (unique ids, every simple scene has
  beats, every complex scene has sub-scenes with beats). With
  `--no-decompose`, complex scenes are coerced to simple by flattening
  sub-scene beats.
- The plan is persisted to `output/<run_id>/plan.json`.

### Phase 2 — Parallel scene rendering

For each `ScenePlanItem`, `scene_runner.run_scene` is called concurrently
(bounded by `asyncio.Semaphore(parallelism)`, default 4):

- **Simple scene**: one call to `scene_worker.render_scene`.
- **Complex scene**: render every sub-scene through the worker, concatenate
  their mp4s with `ffmpeg`, run a continuity-mode judge on the joined clip.

Inside `scene_worker.render_scene`, for up to `max_attempts` (default 4):

1. **Code generation.**
   - Attempt 1: initial generation from `WORKER_SCENE_PROMPT` + the per-scene
     brief.
   - On render failure: `_generate_repair_after_render` — feeds the broken
     code and last 3 KB of stderr back to Gemini.
   - On judge failure: `_generate_repair_after_judge` — feeds the previous
     code and the formatted judge issues back to Gemini.
2. **Normalisation.**
   - `_ensure_scene_class` renames the class if the model picked something
     other than the expected PascalCase slug.
   - `_normalize_tts` rewrites any `GTTSService` import/call to
     `GeminiTTSService(voice="Aoede")` — guards against the model falling
     back to the legacy gTTS pattern from the base system prompt.
3. **Render** with `tools.render_manim_scene` (subprocess `manim -q<l|m|h|k>
   --disable_caching`, with `PYTHONPATH` set so the generated file can import
   `src.agents.tts`). The resulting mp4 is copied to a stable path
   (`output/<run_id>/scene_<id>.mp4`) so later phases can find it.
4. **Judge** (if `--judge`, default on). N frames sampled at evenly-spaced
   midpoints; sent multimodally to Gemini together with the planned beats,
   the description, the `correctness_checks`, and the relevant
   `shared_objects`. Returns `JudgeReport` — must have zero medium/high
   issues to pass.
5. If the judge passes, return `SceneResult(success=True, …)`. Otherwise
   loop with the judge hints as repair input.

**Best-effort fallback.** If all `max_attempts` are exhausted, the worker
returns the most recent attempt that *rendered* successfully (even if the
judge wasn't fully satisfied). This guarantees the stitcher can include the
scene; the master QA loop gets another shot at fixing it.

Every attempt is persisted to `output/<run_id>/judge_<id>_attempt<N>.json`.

### Phase 3 — Stitch

`pipeline._stitch` collects the successful `scene_<id>.mp4` paths in plan
order and concatenates them with `tools.concat_mp4s`. That helper tries
`-c copy` first; if codecs/timebases drift between scenes it falls back to a
re-encode (`libx264 crf=20`, `aac 192k`).

Output: `output/<run_id>/final.mp4` (v1).

### Phase 4 — Master QA + auto-patch loop

Up to `--patch-passes` (default 2) iterations of:

1. **Deterministic QA** (`master.deterministic_qa`, no LLM): flags missing
   renders, render failures, per-scene duration drift > 40%, total-duration
   drift > 30%.
2. **Continuity check** (`continuity.check_continuity`, when
   `shared_objects` exist and ≥ 2 scenes succeeded): for every adjacent
   `(scene_N, scene_N+1)` pair, extract the last frame of N (0.3s before
   end) and the first frame of N+1 (0.3s in), feed both images plus the
   shared-objects spec to Gemini, get back a list of continuity issues
   (kind: `continuity_geometry | continuity_color | continuity_label |
   continuity_missing | continuity_style`). By default the *later* scene is
   targeted for the fix, since "narrative flows forward".
3. **Master QA review** (`master.qa_review`): the LLM gets the full plan,
   per-scene results, and the deterministic + continuity issues, and emits
   a `QAReport` focused on cross-scene flow and pacing.
4. **Stop condition.** If `qa_report.overall_ok` AND no medium/high
   deterministic-or-continuity issues, the loop exits.
5. **Patch.** Otherwise, every `fix_hint` for a non-global scene is collected
   and sent back to `scene_worker.render_scene` as `extra_brief` (appended
   to the worker's user message under a `# MASTER PATCH NOTES` heading).
   Affected scenes are re-rendered in parallel; the result list is
   patched-in by id and the video is **re-stitched**.

Each pass is logged to `output/<run_id>/patch_log.json`. `qa.json` is
overwritten with the latest report.

### Optional — background music

If `--music <path>` is passed, `src/music.py::add_background_music` mixes
a music bed under the final video with ffmpeg (`-22 dB` by default,
1.5s fade-in, 2.0s fade-out, looped if shorter than video).

---

## 6. The custom Gemini TTS adapter (`src/agents/tts.py`)

The pipeline does **not** use the gTTS or ElevenLabs services that ship with
`manim-voiceover` — it ships `GeminiTTSService`, a `SpeechService` subclass
that calls `gemini-2.5-flash-preview-tts` directly via `google-genai`.

Implementation notes:

- Voices are passed as `prebuilt_voice_config(voice_name=…)`. Eight voices
  are advertised in the planner prompt: Aoede (default), Puck, Charon, Kore,
  Fenrir, Leda, Orus, Zephyr.
- The model returns inline PCM 16-bit / 24 kHz / mono. We wrap that in a WAV
  header in-memory, then re-export as MP3 with `pydub`. The MP3 detour is
  required because `manim-voiceover` reads duration via `mutagen.mp3.MP3`.
- An optional `style_prompt` is prepended to the input text to bias delivery.
- Caching honours `manim-voiceover`'s `get_cached_result` — repeated runs of
  the same beat won't re-call the API.

`src/narrator.py` keeps standalone helpers for `edge-tts`, `gTTS`, and
ElevenLabs; not wired into the pipeline today, but available for one-off
use.

---

## 7. The base "battle-tested" worker prompt (`src/gemini_agent.py`)

The `SYSTEM_PROMPT` at the top of `gemini_agent.py` predates the multi-agent
work and is reused as the worker's foundation. It encodes hard-won rules
about Manim Community v0.20+:

- **Layout zones** — title/caption/center, with `to_edge` and `next_to`
  rules to prevent overlap.
- **Banned API calls** — `Indicate(scale=…)`, `Circumscribe(fade_out=…)`,
  `FadeIn(scale=…)`, `get_part_by_tex`, etc.
- **Strict LaTeX rules** — raw strings only, amsmath subset only, highlight
  via separate `MathTex` arguments instead of `get_parts_by_tex`.
- **Named colors only** — BLUE / YELLOW / RED / …
- **Output format** — Python only, no fences, no commentary, first line
  must be `from manim import *`.

The base prompt itself targets `GeminiTTSService` directly (the project's
TTS contract is "always Gemini AI voice" — no gTTS / edge-tts / ElevenLabs).
`src/agents/prompts.py::_strip_gtts_from_base` is kept as a defensive no-op
in case the prompt is edited back. `_WORKER_HEADER_OVERRIDE` then appends
multi-agent-specific instructions:

- Mandatory `set_speech_service(GeminiTTSService(voice=...))` as the first
  line of `construct()`.
- Beat faithfulness — one `with self.voiceover(text=beat.text) as tracker:`
  block per beat, in order, text VERBATIM, animations using
  `run_time=tracker.duration`.
- Correctness checks treated as acceptance criteria.
- Shared-objects rules — vertices/color/label drawn EXACTLY per spec; any
  divergence is a high-severity continuity bug.

---

## 8. Quality gates summary

| Gate                | When it runs                          | What it checks                                                  | Severity that gates progress |
| ------------------- | ------------------------------------- | --------------------------------------------------------------- | ---------------------------- |
| Render success      | Every worker attempt                  | Subprocess `manim` exits 0 and produces an mp4                  | Hard fail → repair           |
| Per-scene Judge     | Every successful render               | Layout, geometry, narration match, duration, correctness checks, shared-objects fidelity | medium/high → repair |
| Continuity-mode Judge | After concatenating sub-scenes      | Continuity across the joined clip                               | non-blocking (logged)        |
| Deterministic QA    | Each patch pass                       | Missing renders, render fails, ±40% scene drift, ±30% total drift | medium/high → patch       |
| Continuity check    | Each patch pass (if shared_objects)   | Last/first-frame comparison for shared objects                  | medium/high → patch          |
| Master QA           | Each patch pass                       | Cross-scene narrative flow, pacing                              | medium/high → patch          |

Patch budget: `--patch-passes` (default 2). Per-scene retry budget:
`--max-attempts` (default 4). When budgets are exhausted the system exits
with whatever the best-effort fallback produced so the user always gets a
playable mp4.

---

## 9. CLI surface (`scripts/generate.py`)

```
python scripts/generate.py "Explain the Fourier transform"
```

Common flags:

| Flag                 | Default            | Purpose                                       |
| -------------------- | ------------------ | --------------------------------------------- |
| `--quality l/m/h/k`  | `l`                | Manim render quality (480p15 → 4K60)          |
| `--model`            | `gemini-2.5-pro`   | Gemini model id used by every agent           |
| `--parallelism`      | `4`                | Concurrent scene workers                      |
| `--max-attempts`     | `4`                | Per-scene retry budget                        |
| `--patch-passes`     | `2`                | Master-QA auto-patch limit                    |
| `--qa / --no-qa`     | `--qa`             | Run the master QA loop                        |
| `--judge / --no-judge` | `--judge`        | Run the per-scene visual judge                |
| `--judge-frames`     | `8`                | Frames sampled per scene for the judge        |
| `--no-decompose`     | off                | Disable complex/sub-scene splitting           |
| `--scenes N`         | 0 (planner decides) | Hint for top-level scene count               |
| `--voice`            | from planner       | Override the Gemini TTS voice                 |
| `--run-id`           | timestamp + slug   | Override the run id (controls artifact dirs)  |
| `--music <path>`     | none               | Mix a background music bed under the final    |
| `--simple`           | off                | Use the legacy single-shot generator instead  |
| `--preview/--no-preview` | `--preview`    | `open` the final mp4 when done (macOS)        |

---

## 10. Configuration (`.env`)

Copy `.env.example` → `.env` and fill in:

- `GOOGLE_API_KEY` — required; used by the planner, workers, judge,
  continuity agent, master QA, **and** the TTS adapter.
- `GOOGLE_GENAI_USE_VERTEXAI` — default `false` (AI Studio). Set to `true`
  with `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` to use Vertex.
- `GEMINI_MODEL` — default `gemini-2.5-pro`. CLI `--model` overrides.
- `ELEVENLABS_API_KEY` — only needed for the standalone `narrator.py`
  helper; the pipeline doesn't use it.
- `DEFAULT_QUALITY`, `OUTPUT_DIR` — for the simple-mode legacy path.

System dependencies: `cairo`, `pango`, `ffmpeg`, optionally `MacTeX` /
`BasicTeX` for LaTeX-rendered math, `sox` (used by `manim-voiceover`).

---

## 11. Progress so far (commit history)

```
3798151  Few fixes
f3dcc9c  Temoral Knowledge
f3f2994  Mutli-Agent System Added
```

Three commits to date:

1. **`f3f2994` — Multi-agent system added.** The architectural leap from
   single-shot generation to the planner / worker / judge / QA pipeline
   described in this doc.
2. **`f3dcc9c` — Temporal knowledge.** Cross-scene continuity work —
   `SharedObject` schema, the continuity agent, judge awareness of shared
   objects, master-QA integration of continuity issues.
3. **`3798151` — Few fixes.** Stabilisation pass.

The working tree under `scenes/` shows several runs already produced under
the new pipeline (timestamped run-id directories from `2026-04-29`), each a
multi-scene attempt at the same families of topics (sum 1+2+…+n, area of a
circle = πr², π in the normal distribution). These are good test cases —
they exercise both the simple flow and complex/sub-scene decomposition with
shared objects (the unrolled-triangle example in particular).

Legacy single-shot scenes (`piinnormaldistribution.py`,
`piinthenormaldistribution.py`, `unrollcirclearea.py`,
`generatedscene.py`) live at the top of `scenes/` from before the
per-run-id subdirectory convention.

---

## 12. Notable design decisions

- **`google-genai` over ADK.** Conceptually we have "agents", but every
  role just needs structured JSON. `genai.Client.generate_content(...,
  response_schema=...)` is simpler, faster, and gives us deterministic
  JSON without ADK's tool-calling overhead. ADK is referenced in the
  README and `requirements.txt` but the pipeline doesn't import it.
- **Schemas kept minimal.** Gemini's structured-output constraint solver
  rejects schemas with too many states (long enums, deep nesting,
  `minItems` / `maxItems`, `propertyOrdering`). The schemas in
  `schemas.py` describe only the JSON shape; everything else is policed
  via the prompt and `_validate_plan`.
- **Best-effort fallback in the worker.** A scene that renders but flunks
  the judge is still returned as `success=True` with the most recent
  rendered mp4. The patch loop gets another chance; the user always gets
  a playable final video.
- **Stable per-scene mp4 paths.** Each rendered scene is copied to
  `output/<run_id>/scene_<id>.mp4` immediately after render. The stitcher
  and continuity agent both rely on these stable paths, decoupled from
  manim's deeply nested `media/videos/<stem>/<quality>/<class>.mp4`
  output tree.
- **MP3 detour for TTS.** Gemini TTS hands back PCM, but
  `manim-voiceover`'s duration probe only understands MP3 — so we wrap
  PCM in WAV in memory, then re-export as MP3 via pydub. The detour is
  cheap and keeps us on the published `manim-voiceover` cache contract.
- **`--no-decompose` escape hatch.** Sub-scene rendering is the most
  expensive code path (one worker per sub-scene, plus a continuity-mode
  judge on the concatenation). The flag flattens any "complex" plan back
  to "simple" beats so users can skip it for cheap iteration.
- **Cross-scene continuity gates the patch loop, not the worker.** The
  continuity check runs against final per-scene mp4s, after all workers
  have settled. That avoids re-rendering a scene many times for a
  mismatch its neighbour caused, and keeps the per-scene worker feedback
  loop fast and local.

---

## 13. Quick start

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # add GOOGLE_API_KEY

# Smoke test the install
manim -pql scenes/example.py SquareToCircle

# Generate a video with the multi-agent pipeline
python scripts/generate.py "Show why the area of a circle is pi r squared" \
    --quality l --parallelism 4 --patch-passes 2

# Or fall back to the single-shot legacy generator
python scripts/generate.py "Explain Euler's identity" --simple
```

The final video is at `output/<run_id>/final.mp4`; on macOS it auto-opens
unless `--no-preview` is passed.
