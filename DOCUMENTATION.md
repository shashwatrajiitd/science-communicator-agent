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

The pipeline is a fan-out / fan-in graph: one planner produces a `ScenePlan`,
N workers render scenes in parallel each with its own judge gate, then a
master QA loop iteratively patches scenes that fail post-stitch checks.

```mermaid
flowchart TD
    T([topic]) --> P[Master Planner<br/>gemini-2.5-pro]
    P -->|ScenePlan JSON| MODE{mode}
    MODE -->|sequential default| SEQ[scene N → scene N+1<br/>with PriorContext handoff]
    MODE -->|--parallel| FANOUT{{"asyncio.Semaphore<br/>(parallelism=4)"}}

    SEQ --> W[Tool-use Worker<br/>render_manim, extract_frames,<br/>probe_audio, compare_to_prior_frame,<br/>web_search, done]
    W --> R[manim render]
    R --> DV{done() validation}
    DV -.fail.-> W
    DV -->|pass| VR[**Full-video reviewer**<br/>upload mp4 → Gemini Files API<br/>media_resolution=LOW]
    VR -.fail.-> W
    VR -->|pass / cap reached| OK[scene_id.mp4]

    FANOUT --> W1[Worker 01<br/>legacy text-repair]
    FANOUT --> W2[Worker 02]
    FANOUT --> WN[Worker NN]
    W1 --> R1[manim render]
    W2 --> R2[manim render]
    WN --> RN[manim render]
    R1 --> J1[Frame Judge 01]
    R2 --> J2[Frame Judge 02]
    RN --> JN[Frame Judge NN]

    OK --> S[ffmpeg concat]
    J1 --> S
    J2 --> S
    JN --> S
    S --> V1[/final.mp4 v1/]

    V1 --> QA[Master QA + Continuity<br/>deterministic + vision on<br/>adjacent boundaries]
    QA -->|overall_ok| DONE([final.mp4])
    QA -->|issues found| PATCH[Patch failing scenes<br/>re-run Worker<br/>(reviewer skipped)]
    PATCH --> RES[re-stitch] --> QA

    classDef llm fill:#e1f0ff,stroke:#3b82f6,color:#000
    classDef io fill:#fef3c7,stroke:#d97706,color:#000
    classDef artifact fill:#dcfce7,stroke:#16a34a,color:#000
    classDef new fill:#fde9ff,stroke:#a855f7,color:#000
    class P,J1,J2,JN,QA,W,W1,W2,WN llm
    class R,R1,R2,RN,S,RES,DV io
    class V1,DONE,T,OK artifact
    class VR new
```

Five LLM-driven roles, each implemented as a plain async function around
Gemini structured output:

| Role           | Module                        | Model used                              | Output                |
| -------------- | ----------------------------- | --------------------------------------- | --------------------- |
| Planner        | `src/agents/master.py`        | gemini-2.5-pro                          | `ScenePlan`           |
| Worker         | `src/agents/scene_worker.py`  | gemini-2.5-pro (function-calling)       | Python file           |
| Judge (legacy) | `src/agents/judge.py`         | gemini-2.5-pro (multimodal frames)      | `JudgeReport`         |
| Video reviewer | `src/agents/video_reviewer.py`| gemini-2.5-pro (multimodal video)       | `VideoReviewReport`   |
| Continuity     | `src/agents/continuity.py`    | gemini-2.5-pro (multimodal frames)      | issue list            |
| Master QA      | `src/agents/master.py`        | gemini-2.5-pro                          | `QAReport`            |

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
│       ├── scene_worker.py  # tool-use worker + post-done() reviewer loop
│       ├── scene_worker_tools.py # FunctionDeclarations + dispatcher
│       ├── judge.py         # legacy frame-based judge (parallel path)
│       ├── video_reviewer.py # full-video reviewer (post-done(), plan-mode)
│       ├── continuity.py    # cross-scene boundary check
│       ├── plan_mode.py     # human-in-the-loop callbacks (--plan-mode)
│       ├── log.py           # rich-styled scope logger
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
├── plan.json                                  # the ScenePlan from the planner
├── qa.json                                    # the latest QAReport
├── continuity.json                            # cross-scene boundary issues
├── patch_log.json                             # what was re-rendered and why
├── reviews.jsonl                              # plan-mode operator action log
├── scene_<id>.mp4                             # one stable mp4 per scene (concat input)
├── scene_<id>.result.json                     # sub-scene cache sidecar
├── <scene_id>/
│   ├── attempts/<NN>/                         # per-render-attempt artifacts (tool-use)
│   │   ├── scene.py                           # code passed to render_manim
│   │   ├── scene.mp4                          # rendered video
│   │   ├── log_tail.txt                       # last 2000B of manim stderr
│   │   └── frames/                            # extract_frames output
│   ├── last_frame.png                         # handoff to scene N+1
│   ├── video_review_round_<N>.json            # automated review verdicts
│   └── video_review_planmode_<N>.json         # plan-mode comment translations
├── frames_<id>_attempt<N>/                    # legacy parallel-path frames
├── continuity_frames/                         # last/first frames of adjacent scenes
├── judge_<id>_attempt<N>.json                 # legacy judge reports per attempt
└── final.mp4                                  # ← the deliverable
```

When each artifact lands during a run:

```mermaid
flowchart LR
    P[Phase 1<br/>Plan] -->|writes| A1[plan.json]
    W[Phase 2<br/>Workers] -->|per attempt| A2[frames_id_attemptN/]
    W -->|per attempt| A3[judge_id_attemptN.json]
    W -->|on success| A4[scene_id.mp4]
    S[Phase 3<br/>Stitch] -->|writes| A5[final.mp4 v1]
    Q[Phase 4<br/>Master QA loop] -->|writes| A6[continuity_frames/]
    Q -->|writes| A7[continuity.json]
    Q -->|each pass| A8[qa.json]
    Q -->|each pass| A9[patch_log.json]
    Q -->|overwrites| A5
```

---

## 4. The data model (`src/agents/schemas.py`)

Every agent boundary is a dataclass with a matching JSON schema. The schemas
are passed to Gemini as `response_schema=` so we get back valid JSON.

### Object relationships

```mermaid
erDiagram
    SCENEPLAN ||--o{ SCENEPLANITEM : "contains scenes"
    SCENEPLAN ||--o{ SHAREDOBJECT : "declares"
    SCENEPLANITEM ||--o{ NARRATIONBEAT : "simple → has beats"
    SCENEPLANITEM ||--o{ SUBSCENE : "complex → splits into"
    SUBSCENE ||--o{ NARRATIONBEAT : "has beats"
    SHAREDOBJECT }o--o{ SCENEPLANITEM : "appears_in"
    SCENEPLANITEM ||--|| SCENERESULT : "produces"
    SCENERESULT ||--|| JUDGEREPORT : "last_judge"
    JUDGEREPORT ||--o{ JUDGEISSUE : "issues"
    SCENEPLAN ||--o{ QAREPORT : "evaluated by"
    QAREPORT ||--o{ QAISSUE : "issues"
```

### `ScenePlan` — the planner's output

```mermaid
classDiagram
    class ScenePlan {
        +str topic
        +str title
        +int total_target_seconds
        +str voice
        +list~ScenePlanItem~ scenes
        +list~SharedObject~ shared_objects
    }
    class ScenePlanItem {
        +str id
        +str slug
        +str description
        +int target_seconds
        +list~str~ key_visuals
        +list~str~ correctness_checks
        +Literal complexity
        +list~NarrationBeat~ beats
        +list~SubScene~ sub_scenes
    }
    class SubScene {
        +str id
        +str slug
        +int target_seconds
        +list~NarrationBeat~ beats
    }
    class NarrationBeat {
        +str text
        +str animation_hint
    }
    class SharedObject {
        +str name
        +str color
        +str label
        +str spec
        +list~str~ appears_in
    }
    ScenePlan "1" *-- "many" ScenePlanItem
    ScenePlan "1" *-- "many" SharedObject
    ScenePlanItem "1" *-- "many" NarrationBeat : when simple
    ScenePlanItem "1" *-- "many" SubScene : when complex
    SubScene "1" *-- "many" NarrationBeat
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
success, last_error, last_judge: JudgeReport, ending_state: str,
last_frame_path: Path, final_review: dict | None)`.

`final_review` is the serialized `VideoReviewReport` from the post-done()
reviewer (None when the reviewer was disabled or the legacy parallel path
ran). `ending_state` and `last_frame_path` feed the next scene's
`PriorContext`.

### `VideoReviewReport` — full-video industry-bar gate

```mermaid
classDiagram
    class VideoReviewReport {
        +bool passed
        +str overall_assessment
        +list~VideoReviewIssue~ issues
        +str delivery
    }
    class VideoReviewIssue {
        +Severity severity
        +ReviewKind kind
        +float t_start_s
        +float t_end_s
        +str description
        +str fix_hint
    }
    class ReviewKind {
        <<enumeration>>
        animation_timing
        narration_sync
        text_readability
        motion_quality
        color_palette
        math_correctness
        continuity
        composition
        pacing
        other
    }
    class Severity {
        <<enumeration>>
        low
        medium
        high
        critical
    }
    VideoReviewReport "1" *-- "many" VideoReviewIssue
    VideoReviewIssue ..> ReviewKind : kind
    VideoReviewIssue ..> Severity : severity
```

`delivery` records which path produced the verdict — `"video"` (the Files
API upload at `media_resolution=MEDIA_RESOLUTION_LOW` succeeded) or
`"frames_fallback"` (the upload failed, so 8 PNGs were sent with the same
prompt instead).

`t_start_s`/`t_end_s` carry timestamps that survive into
`format_video_review_hints()` so the worker's repair instruction reads
"fix the camera jitter at 4.2s–5.8s" not "fix the camera jitter mid-scene".

### `JudgeReport` — per-scene visual gate (legacy)

```mermaid
classDiagram
    class JudgeReport {
        +bool passed
        +str overall_assessment
        +list~JudgeIssue~ issues
    }
    class JudgeIssue {
        +Kind kind
        +Severity severity
        +str where
        +str description
        +str fix_hint
    }
    class Kind {
        <<enumeration>>
        text_overlap
        geometric_error
        narration_mismatch
        off_screen
        wrong_object_count
        duration_mismatch
        color_legibility
        continuity_geometry
        continuity_color
        continuity_label
        continuity_missing
        continuity_style
    }
    class Severity {
        <<enumeration>>
        low
        medium
        high
    }
    JudgeReport "1" *-- "many" JudgeIssue
    JudgeIssue ..> Kind : kind
    JudgeIssue ..> Severity : severity
```

The `fix_hint` field is the load-bearing one — it is fed verbatim back into
the worker as a repair instruction.

### `QAReport` — master/global gate

`(overall_ok: bool, issues: list[QAIssue], notes: str)` — issues here are
cross-scene concerns (pacing, narrative flow, total-duration drift).

---

## 5. End-to-end generation flow

Driver: `src/agents/pipeline.py::run`. All phases are `asyncio` and
`asyncio.to_thread` wraps every blocking SDK / subprocess call.

### End-to-end sequence

The diagram below shows the **legacy parallel path** (`--parallel`,
`--no-tool-worker`) — kept for clarity since it's the simplest mental
model. The default sequential + tool-use path adds a function-calling loop
inside each worker (§9b) and a full-video reviewer gate after `done()`
(§9c); see those sections for the corresponding diagrams.

```mermaid
sequenceDiagram
    autonumber
    actor U as User (CLI)
    participant PL as pipeline.run
    participant MA as master.plan_video
    participant SR as scene_runner
    participant SW as scene_worker
    participant MN as manim (subprocess)
    participant JU as judge
    participant FF as ffmpeg
    participant QA as master.qa_review
    participant CO as continuity

    U->>PL: generate "topic"
    PL->>MA: plan_video(topic)
    MA-->>PL: ScenePlan (persisted plan.json)

    par For each scene (sem=parallelism)
        PL->>SR: run_scene(item)
        SR->>SW: render_scene(item)
        loop up to max_attempts
            SW->>MN: render Python file
            alt render fails
                MN-->>SW: stderr
                SW->>SW: repair_after_render
            else render OK
                SW->>JU: judge(frames, beats, shared_objects)
                JU-->>SW: JudgeReport
                alt passed (no medium/high)
                    SW-->>SR: SceneResult success
                else failed
                    SW->>SW: repair_after_judge(fix_hints)
                end
            end
        end
        SR-->>PL: SceneResult
    end

    PL->>FF: concat scene_{id}.mp4
    FF-->>PL: final.mp4 (v1)

    loop up to patch_passes
        PL->>PL: deterministic_qa(plan, results)
        PL->>CO: check_continuity(adjacent boundary frames)
        CO-->>PL: continuity issues
        PL->>QA: qa_review(plan, results, det+cont)
        QA-->>PL: QAReport
        alt overall_ok and no medium/high issues
            PL->>U: open final.mp4
        else issues remain
            PL->>SW: re-render affected scenes (extra_brief)
            SW-->>PL: patched SceneResults
            PL->>FF: re-stitch
        end
    end
```

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
   `src.agents.tts`). When `--aspect-ratio` is non-default the resolution
   computed by `tools.resolution_for` is appended as `-r W,H` and the output
   is located in the matching `<H>p<fps>/` directory. The resulting mp4 is
   copied to a stable path (`output/<run_id>/scene_<id>.mp4`) so later phases
   can find it.
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

#### Per-scene worker state machine

```mermaid
stateDiagram-v2
    [*] --> GenerateInitial : attempt 1
    GenerateInitial --> Normalize
    Normalize --> Render : ensure class name<br/>rewrite gTTS → Gemini
    Render --> RepairAfterRender : manim non-zero<br/>(stderr → Gemini)
    RepairAfterRender --> Normalize : new code
    Render --> Judge : mp4 produced
    Judge --> Done : passed (no medium/high)
    Judge --> RepairAfterJudge : medium/high issues
    RepairAfterJudge --> Normalize : new code

    Render --> BestEffort : attempts exhausted<br/>+ at least one render OK
    Judge --> BestEffort : attempts exhausted<br/>+ at least one render OK
    RepairAfterRender --> Failed : attempts exhausted<br/>+ no render ever OK
    RepairAfterJudge --> BestEffort : attempts exhausted

    Done --> [*]
    BestEffort --> [*] : success=True<br/>(latest rendered mp4)
    Failed --> [*] : success=False
```

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

#### Patch-loop decision flow

```mermaid
flowchart TD
    START([final.mp4 v1]) --> DET[deterministic_qa]
    DET --> CONT{shared_objects<br/>present?}
    CONT -- yes --> CC[continuity check<br/>last/first frame pairs]
    CONT -- no --> QA
    CC --> QA[master.qa_review]
    QA --> GATE{overall_ok AND<br/>no medium/high<br/>det+continuity issues?}
    GATE -- yes --> SHIP([ship final.mp4])
    GATE -- no --> BUDGET{passes left?}
    BUDGET -- no --> SHIP
    BUDGET -- yes --> COLLECT[collect fix_hints<br/>by scene id]
    COLLECT --> PATCH[re-render affected<br/>scenes in parallel]
    PATCH --> STITCH[re-stitch]
    STITCH --> DET

    classDef gate fill:#fee2e2,stroke:#dc2626,color:#000
    classDef done fill:#dcfce7,stroke:#16a34a,color:#000
    class GATE,BUDGET,CONT gate
    class SHIP,START done
```

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

| Gate                  | When it runs                          | What it checks                                                                              | Severity that gates progress  |
| --------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------- |
| Render success        | Every worker attempt                  | Subprocess `manim` exits 0 and produces an mp4                                              | Hard fail → repair            |
| `done()` validation   | Every `done()` call (tool-use path)   | Video exists, ≥1 KB, ffprobe-readable, duration ≥ 0.5s, audio present                       | Reject → next render          |
| Per-scene Judge       | Every successful render (parallel path only) | Layout, geometry, narration match, duration, correctness checks, shared-objects fidelity | medium/high → repair          |
| **Full-video reviewer** | After `done()` accepts (sequential path, default on) | Animation timing, narration sync, text readability, motion quality, math correctness, color palette, prior-scene continuity. Returns timestamped fix_hints. | high/critical (any) → resume tool loop with feedback, capped at `--max-review-rounds` |
| Continuity-mode Judge | After concatenating sub-scenes        | Continuity across the joined clip                                                           | non-blocking (logged)         |
| Deterministic QA      | Each patch pass                       | Missing renders, render fails, ±40% scene drift, ±30% total drift                           | medium/high → patch           |
| Continuity check      | Each patch pass (if shared_objects)   | Last/first-frame comparison for shared objects                                              | medium/high → patch           |
| Master QA             | Each patch pass                       | Cross-scene narrative flow, pacing                                                          | medium/high → patch           |

### Where each gate sits

```mermaid
flowchart LR
    subgraph PerScene["Per-scene loop (sequential + tool-use)"]
        direction TB
        G1[Render success] --> G1b[done() validation]
        G1b --> G1c[Full-video reviewer<br/>industry-bar gate<br/>upload mp4 → timestamped issues]
        G1c -.fail.-> G1[resume tool loop<br/>with formatted hints]
        G1c -.legacy parallel.-> G2[Per-scene Judge<br/>frame-based]
        G2 -.sub-scenes only.-> G3[Continuity-mode Judge]
    end
    subgraph Global["Patch loop (post-stitch)"]
        direction TB
        G4[Deterministic QA] --> G5[Continuity check]
        G5 --> G6[Master QA]
    end
    PerScene --> Stitch[ffmpeg concat] --> Global
    Global -->|issues| PerScene
    Global -->|clean| Ship([final.mp4])

    classDef hard fill:#fee2e2,stroke:#dc2626,color:#000
    classDef soft fill:#fef3c7,stroke:#d97706,color:#000
    classDef new fill:#e1f0ff,stroke:#3b82f6,color:#000
    class G1,G1b,G4 hard
    class G2,G3,G5,G6 soft
    class G1c new
```

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
| `--aspect-ratio` / `--aspect` | `16:9`    | Output aspect ratio: `16:9`, `9:16`, `1:1`, `4:5`, `21:9`, … |
| `--parallel / --no-parallel` | `--no-parallel` | Render scenes in parallel (legacy). Default is sequential. |
| `--tool-worker / --no-tool-worker` | `--tool-worker` | Use the Gemini function-calling self-validating worker.  |
| `--max-tool-iterations` | `12`          | Hard ceiling on tool calls per scene (tool-use worker only). |
| `--video-review / --no-video-review` | `--video-review` | Run the full-video reviewer after `done()`; loop the worker on failure. |
| `--max-review-rounds` | `2`             | Cap on review rounds per scene before accepting current render. |
| `--video-review-model` | `gemini-2.5-pro` | Model used by the post-done() reviewer + plan-mode comment translation. |
| `--adviser-model` | `gemini-3.1-pro-preview` | Escalation target after `--escalate-after-render-failures` total render_manim calls without `done()`. |
| `--escalate-after-render-failures` | `4` | Total `render_manim` calls before swapping to the adviser model. |

---

## 9a. Aspect-ratio control

Both pipeline paths accept an `--aspect-ratio` (alias `--aspect`) flag. The
spec is parsed by `tools.parse_aspect_ratio` (accepts `:`, `x`, or `/` as a
separator) into a `(W, H)` tuple, and `tools.resolution_for(aspect, quality)`
maps it to a pixel resolution. Manim is invoked with `-r W,H` and the worker
brief is augmented with orientation-specific layout guidance.

### Resolution policy

The **short side** is anchored to the `--quality` preset. This matches the
colloquial meaning of "1080p" (vertical pixels in landscape, horizontal pixels
in portrait), so `-q h` always gives a "1080p-class" video regardless of
aspect:

| `--quality`       | short side | 16:9       | 9:16       | 1:1        | 4:5        | 21:9        |
| ----------------- | ---------- | ---------- | ---------- | ---------- | ---------- | ----------- |
| `l` (480p15)      | 480 px     | 854×480    | 480×854    | 480×480    | 480×600    | 1120×480    |
| `m` (720p30)      | 720 px     | 1280×720   | 720×1280   | 720×720    | 720×900    | 1680×720    |
| `h` (1080p60)     | 1080 px    | 1920×1080  | **1080×1920** | 1080×1080 | 1080×1350 | 2520×1080   |
| `k` (2160p60)     | 2160 px    | 3840×2160  | 2160×3840  | 2160×2160  | 2160×2700  | 5040×2160   |

The long side is rounded to the nearest even pixel (libx264 requirement).

### How the aspect flows through the pipeline

```mermaid
flowchart LR
    CLI["scripts/generate.py<br/>--aspect 9:16 -q h"] -->|aspect_ratio str| PL[pipeline.run]
    CLI -->|"parse_aspect_ratio<br/>+ resolution_for"| RES["(1080, 1920)"]
    PL -->|aspect_ratio + resolution| SR[scene_runner.run_scene]
    SR -->|aspect_ratio + resolution| SW[scene_worker.render_scene]
    SW -->|aspect_ratio + resolution| BRIEF[build_worker_user_message<br/>+ _aspect_block]
    SW -->|resolution| TOOL["tools.render_manim_scene<br/>manim ... -r W,H"]
    BRIEF --> LLM["Gemini worker<br/>(layout-aware code)"]
    LLM --> SCENE[Manim Scene file]
    SCENE --> TOOL
    TOOL --> MP4[scene_id.mp4]

    classDef io fill:#fef3c7,stroke:#d97706,color:#000
    classDef llm fill:#e1f0ff,stroke:#3b82f6,color:#000
    classDef artifact fill:#dcfce7,stroke:#16a34a,color:#000
    class CLI,TOOL io
    class LLM llm
    class MP4,SCENE,RES artifact
```

### Worker layout guidance

`prompts._aspect_block` injects a context block into the per-scene brief.
Manim keeps `frame_height = 8.0` and scales `frame_width = 8 * W / H`, so
portrait formats produce a much narrower scene-width that can break the
default 3Blue1Brown layout. The block surfaces:

- the chosen aspect ratio + pixel resolution,
- the resulting Manim `frame_width` in scene units (e.g. `4.5` for 9:16,
  `8.0` for 1:1, `14.22` for 16:9),
- orientation-specific tips:
  - **portrait** → favour `VGroup(...).arrange(DOWN)`, wrap text to ~25 chars,
    avoid absolute x-coords beyond `±frame_width/2`, smaller `to_edge` buff;
  - **square** → center the main visualization at `ORIGIN`, fit equations
    inside the central ~70%;
  - **landscape** → standard horizontal layout (status quo).

These hints land in the same brief that already carries beats, key visuals,
correctness checks, and shared-objects specs, so the LLM treats them as
first-class layout constraints rather than free-form advice.

---

## 9b. Sequential pipeline + self-validating tool-use worker

The default pipeline (since v2) runs scenes **sequentially** and gives every
worker a Gemini **function-calling toolbelt** so it can render and inspect its
own output before declaring done. The legacy parallel path is still available
behind `--parallel` for fast batch runs that don't need cross-scene continuity.

### Why sequential

Workers used to fly blind across scene boundaries. The asyncio.gather path
means scene N+1 starts before scene N finishes — its prompt has no idea what
mobjects are on screen at the cut, what naming conventions the prior worker
chose, or what camera state to inherit. The post-hoc continuity check in
`continuity.py` catches drift, but only after every scene has already been
rendered (and re-rendering is what we're trying to avoid).

In sequential mode (`pipeline._run_sequential`) each scene completes before
the next starts; on success we capture an `ending_state` summary (the model
writes it as the argument to its `done()` tool call) and the last frame of
the rendered video, and hand both to the next worker.

### Why tool-use

The text-only worker in `scene_worker.render_scene` is a 4-attempt loop:
generate code → render → if failure, send the stderr back as text → regenerate.
The model never sees the rendered video, just an error message. Geometric
problems ("the triangle came out as a parallelogram"), missing audio, or
continuity drift can only be flagged by the downstream judge — too late.

`scene_worker.render_scene_with_tools` flips this. The model gets a Gemini
`Tool` with five `FunctionDeclaration`s and is forced into `mode=ANY` (no
free-text replies). It iterates: render, inspect frames, probe audio, compare
to prior frame, fix, re-render — until it calls `done(video_path, summary)`.

### Tool inventory

Defined in `src/agents/scene_worker_tools.py`:

| Tool | Returns | Use |
|------|---------|------|
| `render_manim(code, scene_class)` | `success`, `log_tail`, `video_path`, `duration_s` | Write code to fresh attempt dir, run manim |
| `extract_frames(video_path, n)` | list of `{t_seconds, path}` | Sample N PNGs to inspect |
| `probe_audio(video_path)` | `has_audio`, `duration_s` | Verify voiceover rendered |
| `compare_to_prior_frame(this_frame_path)` | `diff_summary` (text) | Vision-diff vs prior scene's last frame |
| `done(video_path, ending_state_summary)` | `accepted` (bool) | Terminal — required to exit the loop |

Each call lands in `output/<run_id>/<scene_id>/attempts/<NN>/`:

```
attempts/01/
  scene.py        # the code passed to render_manim
  scene.mp4       # rendered video (if success)
  log_tail.txt    # last 2000 chars of manim stdout/stderr
  frames/         # extract_frames output
```

The hard ceiling is `--max-tool-iterations` (default 8). On exhaustion, the
worker returns the most recent successful render as best-effort with an empty
`ending_state` (so the next scene's continuity hint is degraded but the run
still completes).

### Prior-context handoff

`schemas.PriorContext` is the payload threaded between scenes:

```python
PriorContext(
    prior_scene_id="01",
    last_frame_path=Path(".../output/<run_id>/01/last_frame.png"),
    ending_state="Blue circle of radius 2 centred at ORIGIN; label 'r=2' below.",
    prior_code_path=Path(".../scenes/<run_id>/show_circle.py"),
)
```

`prompts._prior_context_block` injects the ending-state text and the prior
scene's full Python source into the next worker's brief. The last frame is
attached separately as a multimodal `Part.from_bytes` so the model literally
sees what the previous scene faded to. The prior code helps the worker match
naming and mobject construction conventions so persistent objects stay visually
identical.

### Sequential vs parallel — flow comparison

```mermaid
flowchart LR
    subgraph Sequential["Sequential (default) — pipeline._run_sequential"]
        S0[plan_video] --> S1[scene 01<br/>tool worker]
        S1 -->|"PriorContext<br/>(last_frame, ending_state, code)"| S2[scene 02<br/>tool worker]
        S2 -->|"PriorContext"| S3[scene 03<br/>tool worker]
        S3 --> S4[stitch + QA]
    end

    subgraph Parallel["Parallel (--parallel) — pipeline.run gather"]
        P0[plan_video] --> P1[scene 01]
        P0 --> P2[scene 02]
        P0 --> P3[scene 03]
        P1 --> P4[stitch + QA + continuity check<br/>post-hoc]
        P2 --> P4
        P3 --> P4
    end
```

### Tool-use loop (per scene)

```mermaid
sequenceDiagram
    participant W as Worker (scene_worker_tools.dispatch)
    participant G as Gemini (mode=ANY)
    participant M as Manim subprocess
    participant FF as ffmpeg/ffprobe

    Note over W,G: brief (text) + prior frame (image) + system prompt
    G->>W: render_manim(code, scene_class)
    W->>M: write code, run manim
    M-->>W: stdout/stderr + mp4 path
    W-->>G: {success, log_tail, video_path, duration_s}

    alt success
        G->>W: extract_frames(video_path, n=4)
        W->>FF: ffmpeg -ss t -frames:v 1 ...
        FF-->>W: PNG paths
        W-->>G: [{t_seconds, path}, ...]

        G->>W: compare_to_prior_frame(first_frame)
        W->>G: (mini vision call: prior vs this)
        G-->>W: diff_summary text
        W-->>G: {diff_summary}

        G->>W: done(video_path, ending_state_summary)
        W-->>G: {accepted: true}
    else failure
        Note over G: read log_tail, fix code, call render_manim again
    end
```

### CLI summary

| Flag | Default | Effect |
|------|---------|--------|
| (none — sequential is default) | sequential | Scenes rendered one at a time, prior-context threaded |
| `--parallel` | off | Restore legacy `asyncio.gather` path; no prior context |
| `--tool-worker` (default on) | on | Use the function-calling worker |
| `--no-tool-worker` | — | Fall back to legacy text-only repair worker (still useful with `--parallel`) |
| `--max-tool-iterations` | `12` | Cap on tool calls per scene |
| `--video-review` (default on) | on | Run the full-video reviewer after `done()` (§9c) |
| `--max-review-rounds` | `2` | Cap on review rounds per scene |

### Hooks for `--plan-mode`

`pipeline.run` accepts two optional callables, both defaulting to no-op pass-
through. `--plan-mode` (§9c) wires them up; you can also build your own
callbacks for non-CLI contexts (notebooks, web UI):

- `pre_plan_approval(plan: ScenePlan) -> ScenePlan` — fired after the planner
  returns. Whatever the callback returns becomes the working plan.
- `post_scene_approval(item, result, rerun) -> SceneResult` — fired after
  each scene completes in sequential mode. `rerun(extra_brief)` is a closure
  the pipeline injects so the callback can request re-renders without
  needing the rest of the run-state. Callable accepts a `str | None`
  (additional brief / no-op retry) and returns the new `SceneResult`.

Both callables can be sync or async — `pipeline._maybe_await` handles either.

---

## 9c. Full-video reviewer (`src/agents/video_reviewer.py`)

The default sequential pipeline ships a per-scene quality gate that watches
the **complete rendered video**, not sampled frames. It runs AFTER the
worker calls `done()` and BEFORE the scene is accepted into the stitcher.

### Why the worker can't be its own reviewer

The tool-use worker decides when to call `done()` based on its own inspection
(rendered frames + audio probe + prior-frame diff). That works for catching
obvious failures — wrong shapes, missing audio, blank frames — but tends to
miss:

- **Animation timing** — jerky transitions, instant snaps that should ease,
  drag durations that don't match the narration.
- **Narration ↔ visual sync** — the voiceover finishes 1.5s before the
  equation appears, or the wave morphs while the line "as the wave morphs"
  still has 0.8s of audio left.
- **Motion smoothness** — frame-rate hiccups invisible in still frames.
- **Subjective composition** — text overflowing the safe zone, off-palette
  colors, cluttered layout.

Eight evenly-spaced PNGs sampled by the legacy frame-judge can't catch any
of these — motion lives between frames. The Gemini Files API can ingest the
whole mp4, sampled by the model itself at low media resolution, and judge
all of the above with timestamps.

### Architecture

```mermaid
sequenceDiagram
    autonumber
    participant SW as scene_worker._run_with_review_loop
    participant TL as _drive_tool_loop
    participant VR as video_reviewer.review_scene_video
    participant FA as Gemini Files API
    participant G as Gemini 2.5 Pro

    SW->>TL: run tool loop until model calls done()
    TL-->>SW: contents, accepted_video, summary

    loop up to --max-review-rounds (default 2)
        SW->>VR: review_scene_video(video, target, plan, prior_frame, prior_code)
        VR->>FA: client.files.upload(file=mp4)
        FA-->>VR: File(name, uri, state=PROCESSING)
        loop poll until ACTIVE
            VR->>FA: client.files.get(name)
            FA-->>VR: File(state=ACTIVE)
        end
        VR->>G: generate_content(<br/>  contents=[Part.from_uri(uri),<br/>            prior_frame_png,<br/>            prompt],<br/>  media_resolution=LOW,<br/>  response_schema=VideoReviewReport<br/>)
        G-->>VR: VideoReviewReport JSON
        VR->>FA: client.files.delete(name)
        VR-->>SW: VideoReviewReport(passed, issues[], delivery)

        alt passed
            SW->>SW: break — finalize SceneResult
        else failed + thrashing detected
            SW->>SW: break — accept current render with unresolved issues
        else failed
            SW->>SW: append synthetic user turn (formatted hints) to contents
            SW->>TL: _drive_tool_loop(contents=...)
            TL-->>SW: new accepted_video, summary
        end
    end

    SW->>SW: extract_last_frame(accepted_video) — AFTER review loop settles
    SW-->>SW: SceneResult(success=True, final_review=report.to_dict())
```

The review feedback is a **synthetic user turn** appended to the existing
`contents` list, then `_drive_tool_loop` is re-invoked with the populated
list. This preserves the model's memory of every render attempt, every tool
response, and every prior reviewer verdict — the model continues the same
conversation rather than starting fresh.

### Review criteria

The system prompt orders the reviewer's priorities (highest first):

1. **Mathematical / factual correctness** — wrong sign, mis-rendered
   exponent, axis scale wrong → `critical` even if the animation looks
   pretty.
2. **Narration ↔ visual sync** — out-of-phase voiceover and animation.
3. **Animation timing & motion quality** — jerky/instant transitions,
   missing easing.
4. **Text readability** — clipping, font weight, hierarchy.
5. **Continuity with prior scene** — when a prior-scene last frame is
   attached, persistent mobjects must keep position/color/geometry.
6. **Composition & color palette** — 3Blue1Brown aesthetic.
7. **Pacing per beat** — long static stretches while narration runs.

The schema requires every issue to carry a `t_start_s`/`t_end_s` range so
the worker's repair instruction is anchored to a specific moment — not "fix
the equation timing" but "shorten the `Write(eq)` `run_time` from 2.0 to
1.0; the equation finishes at 6.4s but the narration moves on at 5.1s".

### Delivery: video upload + frame fallback

Primary path:

```python
uploaded = client.files.upload(file=str(video_path))
# poll uploaded = client.files.get(name=...) until state == ACTIVE
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[Part.from_uri(file_uri=uploaded.uri, mime_type="video/mp4"),
              prior_frame_png, prompt_text],
    config=GenerateContentConfig(
        media_resolution="MEDIA_RESOLUTION_LOW",
        response_mime_type="application/json",
        response_schema=VIDEO_REVIEW_REPORT_SCHEMA,
    ),
)
client.files.delete(name=uploaded.name)   # in finally — even on exception
```

`media_resolution=MEDIA_RESOLUTION_LOW` cuts the per-second video token
spend roughly 3× vs default. For QA the model needs to see motion and read
labels, not pixel detail. Per-scene-per-round cost on a 30s scene at LOW is
typically 8–12k input tokens + 1–3k structured output.

Files-API quota is bounded by `try/finally` cleanup so a flaky run doesn't
fill the account quota.

If upload, polling, or the generate call fails, the same prompt is rerun
with 8 frames sampled via `extract_frames()` and submitted as PNG parts.
The verdict's `delivery` field records which path produced it
(`"video"` vs `"frames_fallback"`). The frames fallback also tells the
model in-prompt that it can't judge motion smoothness — biasing it away
from false positives.

### Thrashing detection

The reviewer can flag issues the model can't actually fix (e.g. manim
limitations, conflicting plan beats). Across rounds we compare the
multi-set of `(severity, kind)` pairs:

```python
def no_progress(prev, curr):
    prev_high = {(i.severity, i.kind) for i in prev.issues if i.severity in ("high", "critical")}
    curr_high = {(i.severity, i.kind) for i in curr.issues if i.severity in ("high", "critical")}
    if not prev_high:
        return False
    return prev_high.issubset(curr_high) and len(curr.issues) >= len(prev.issues)
```

When the prior round's high-severity (kind, severity) pairs ALL still
appear AND the total issue count didn't drop, the loop exits early and the
current render is accepted with its unresolved issues recorded in
`SceneResult.final_review`.

### Persistence

Every round writes a verdict next to the scene's other artifacts:

```
output/<run_id>/<scene_id>/
├── attempts/01/                       # the render that round 1 reviewed
├── attempts/02/                       # the render produced AFTER round 1's hints
├── video_review_round_1.json          # round 1 verdict
├── video_review_round_2.json          # round 2 verdict (if needed)
└── last_frame.png                     # extracted from the FINAL accepted video
```

`SceneResult.final_review` carries the last round's `VideoReviewReport`
serialized as a dict, so plan-mode UX, master QA, and downstream tooling
can all read structured timestamps and severities without re-uploading.

### When the reviewer is skipped

- `--no-video-review` — entirely off; behaves like the pre-reviewer pipeline.
- Master-QA-driven re-renders — the master already produced structured
  `extra_brief` patch hints; running an independent reviewer on top would
  duplicate work and double-spend tokens. `pipeline.run` forces
  `video_review_enabled=False` for those re-render calls.
- The legacy parallel path (`--parallel`) — that path uses the legacy
  frame-based `judge_scene()` instead.

---

## 9d. `--plan-mode`: human-in-the-loop review

The default sequential pipeline (§9b) is fully autonomous. `--plan-mode`
swaps in two interactive gates:

1. **Plan gate** — review the planner's output before any rendering starts.
2. **Per-scene gate** — review every rendered scene before the next starts.

Both gates loop until you approve (or hit a 5-round revision cap, or quit).

```bash
python scripts/generate.py "Why does pi appear in a Gaussian?" --plan-mode
python scripts/generate.py "..." --plan-mode --no-plan-mode-open  # SSH-friendly
```

`--plan-mode` requires sequential mode; passing `--parallel` together is
rejected at CLI parse time.

### Lifecycle

```mermaid
sequenceDiagram
    participant U as Operator
    participant CLI as scripts/generate.py
    participant PM as plan_mode (callbacks)
    participant P as pipeline.run
    participant M as master.plan_video / revise_plan
    participant W as scene worker (tool-use)

    U->>CLI: --plan-mode "topic"
    CLI->>PM: make_callbacks(model, run_id, ...)
    PM-->>CLI: (pre_plan, post_scene)
    CLI->>P: run(parallel=False, pre_plan=..., post_scene=...)

    P->>M: plan_video(topic)
    M-->>P: ScenePlan v1
    P->>PM: pre_plan_approval(plan)

    loop until approved or cap
        PM->>U: rich table (plan)
        U-->>PM: a / c <comment> / q
        alt comment
            PM->>M: revise_plan(plan, comment)
            M-->>PM: ScenePlan v2
        end
    end
    PM-->>P: approved plan

    loop per scene (sequential)
        P->>W: run_scene(item, plan, prior_context)
        W-->>P: SceneResult (with final_review)
        P->>PM: post_scene_approval(item, result, rerun, translate_comment)

        loop until approved or cap
            PM->>U: panel + auto-open mp4
            U-->>PM: a / c <comment> / r / q
            alt comment
                PM->>P: translate_comment(item, result, comment)
                P->>P: review_scene_video(<br/>  user_comment=comment,<br/>  prior_code=...)
                P-->>PM: formatted prose hints
                PM->>P: rerun(extra_brief=hints)
                P->>W: run_scene(... extra_brief)
                W-->>P: SceneResult'
                P-->>PM: SceneResult'
            else retry
                PM->>P: rerun(extra_brief=None)
                P-->>PM: SceneResult'
            end
        end
        PM-->>P: approved result
    end

    P->>P: stitch + (optional) QA
    P-->>CLI: final.mp4
    CLI->>U: print path
```

### CLI surface

| Flag | Default | Effect |
|------|---------|--------|
| `--plan-mode` | off | Enable both gates. Forces `--no-parallel` and force-disables QA. |
| `--no-plan-mode-open` | (off when `--plan-mode-open` is on) | Suppress the `open <path>` call when each scene renders. |
| `--plan-mode-max-rounds N` | `5` | Cap on revision rounds per plan/scene. |
| `--qa` (with `--plan-mode`) | ignored | QA is force-off in plan-mode; you've already approved each scene. |

### Action keys

| Key | Plan gate | Scene gate (clean render) | Scene gate (failed render) |
|-----|-----------|---------------------------|----------------------------|
| `a` | approve plan, continue to render | approve scene, continue to next | **disabled** |
| `c` | comment + revise plan via LLM | comment + reviewer translation + re-render | comment + reviewer translation + re-render |
| `r` | — | retry scene without a comment | retry scene without a comment |
| `q` | abort with exit code 2 | abort with exit code 2 | abort with exit code 2 |

Either the literal letter or the prefix of the label works (`approve`, `comm`,
etc.). Pressing Enter takes the default (`a` for clean renders, `r` for failed).

### Comment translation

When you press `[c]` on a scene gate and type a free-form comment, the
operator's prose is sent to the **video reviewer** (§9c) along with the
rendered mp4 and the previous render's Python source. The reviewer is
prompted to ANCHOR its review on the operator comment but may also surface
any other high-severity issues it spots. The output is a
`VideoReviewReport` with structured timestamps and code-anchored
`fix_hint`s, which is then rendered into prose via
`format_video_review_hints()` and forwarded to the worker as `extra_brief`.

```mermaid
flowchart LR
    OP["operator: 'equation looks weird'"] --> TR[translate_comment closure<br/>built per-scene by pipeline.run]
    TR --> VR[video_reviewer.review_scene_video<br/>user_comment=...,<br/>prior_code=scene.py]
    VR --> RP[VideoReviewReport<br/>passed=false<br/>issues=[3 timestamped fixes]]
    RP --> FH[format_video_review_hints]
    FH --> EB[extra_brief prose<br/>'[high] math_correctness at 7.4s–8.1s:<br/>exponent rendered as -2 instead of 2.<br/>Fix: change MathTex r&#94;2 not r&#94;-2.']
    EB --> W[run_scene rerun]
    W --> SR[new SceneResult]

    classDef llm fill:#e1f0ff,stroke:#3b82f6,color:#000
    classDef io fill:#fef3c7,stroke:#d97706,color:#000
    class VR,FH llm
    class TR,EB io
```

Each translation persists to
`output/<run_id>/<scene_id>/video_review_planmode_N.json` with both the
verbatim operator comment and the reviewer's structured report. If the
reviewer call fails (network, Files API quota, parse error), plan-mode
falls back to passing the raw comment as before — operator intent is
never blocked on reviewer availability.

The translation is gated on `--video-review` being enabled. With
`--no-video-review`, comments are forwarded as raw text exactly as in the
pre-reviewer pipeline.

### Clean-render gate

Approve is disabled until the worker produces an mp4 that meets all of:
1. `result.success == True` (the tool-use worker called `done(...)` and the
   render passed validation).
2. `result.video_path` exists and is non-empty.

The `done(video_path, ending_state_summary)` tool itself enforces a stricter
check before accepting:
- video file exists, ≥ 1 KB
- `ffprobe` reads it without error
- duration ≥ 0.5s
- audio track is present (manim_voiceover wired correctly)

If any of these fail, `done(...)` returns `accepted=false` with a specific
error message. The model is expected to read the error, fix the code, and
call `render_manim` again. The model only returns to plan-mode after a
successful `done(...)`. If `--max-tool-iterations` exhausts without a clean
render, the worker returns `success=False` and plan-mode forces retry/quit
rather than presenting a half-broken scene.

### Persistence

Every action is appended to `output/<run_id>/reviews.jsonl`:

```jsonl
{"ts": "2026-04-29T18:30:00Z", "phase": "plan", "scene_id": null, "action": "comment", "comment": "make scene 02 shorter"}
{"ts": "...", "phase": "plan", "scene_id": null, "action": "approve", "comment": null}
{"ts": "...", "phase": "scene", "scene_id": "01", "action": "approve", "comment": null}
{"ts": "...", "phase": "scene", "scene_id": "02", "action": "comment", "comment": "shrink the square"}
{"ts": "...", "phase": "scene", "scene_id": "02", "action": "approve", "comment": null}
```

Used today only as an audit trail. Resumability across runs and backtracking
to earlier scenes are deferred.

### Gotchas

- **Rendering takes minutes.** Each scene's tool-use loop typically does 1–3
  manim renders, each ~30–120s at `--quality l`. Plan-mode adds prompts but
  doesn't change render cost.
- **API spend on tight comment loops.** Each plan revision is one Gemini
  call; each scene re-render with a comment can be 4–8 Gemini calls plus
  TTS. The 5-round cap protects you from a runaway loop, but a deliberate 5
  rounds × 4 scenes is still ~80 Gemini calls.
- **macOS-only auto-open.** `open <path>` is macOS; `xdg-open <path>` is the
  Linux fallback. Other platforms silently skip.
- **stdin in non-tty contexts.** `typer.prompt` reads from stdin. You can
  pipe approvals (`printf 'a\na\n' | python scripts/generate.py ...`) but
  most users will run interactively. `--plan-mode` over SSH works as long as
  you have stdin and don't need auto-open (`--no-plan-mode-open`).

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

## 11. Test cases and legacy scenes

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
- **The reviewer runs OUTSIDE the `done()` dispatcher, not inside it.**
  An earlier draft put the reviewer call inside `_tool_done` so failed
  reviews would naturally fall back into the function-calling loop. That
  would have made `done()` non-terminal — a 30–60s upload + Gemini call
  inside a tool-response, swallowed by the bare `except` in `dispatch`,
  and the model can't read text in `function_calling_config=ANY` mode so
  it had no way to plan a different approach. We keep `done()` fast and
  deterministic, run the reviewer in `_run_with_review_loop` after
  `_drive_tool_loop` returns, and resume the SAME `contents` list with a
  synthetic user turn carrying the formatted feedback. Preserves the
  model's working memory and keeps the `max_iter` safety net.
- **`last_frame.png` is extracted AFTER the review loop terminates.** If
  the reviewer triggers a re-render on round 1, the round-2 mp4 replaces
  the accepted video — but the prior-context handoff to scene N+1 must
  point at the FINAL accepted video's last frame, not the rejected
  earlier render. We moved `extract_last_frame` past the review loop in
  `_finalize_tool_result` so a stale handoff frame can't propagate.
- **`media_resolution=MEDIA_RESOLUTION_LOW` for video review.** Industry-
  bar judgment needs to see motion and read labels, not pixel detail.
  LOW cuts video tokens roughly 3× vs default. A 30s scene at LOW is
  ~8–12k input tokens of video — affordable to run on every scene at
  every round.
- **Files API cleanup in `try/finally`.** Cleanup-on-success is fine; the
  failure mode that bites is cleanup-on-exception leaving uploads on the
  account quota. `review_scene_video` always deletes the uploaded file
  whether the model call returned, raised, or timed out.
- **Frame fallback shares the prompt with the video path.** If the Files
  API fails, we extract 8 frames and rerun the same review prompt with
  PNG parts instead of a `Part.from_uri`. One source of truth for the
  reviewer prompt; the verdict's `delivery` field records which path
  produced it.
- **Skip the reviewer in master-QA-driven re-renders.** When the master
  patch loop calls `run_scene` with `extra_brief=<patch hints>`, those
  hints already encode structured feedback. Running an independent
  reviewer on top would duplicate work and double-spend tokens. The
  reviewer is gated off for those re-render calls.
- **Plan-mode comment translation reuses the reviewer.** Operator
  comments in `--plan-mode` are vague by design ("equation looks
  weird"). Rather than asking the worker to interpret them, we route the
  comment through the same `review_scene_video` function with the
  comment as a strong prior and the previous render's source code as
  context. The reviewer outputs structured timestamped fix hints which
  are formatted into the same prose shape the automated review loop
  produces — the worker sees one consistent feedback format whether the
  origin was an LLM verdict or an operator's nudge.

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

# Generate vertically (Shorts / Reels / TikTok) at 1080×1920
python scripts/generate.py "Why does pi appear in a Gaussian?" \
    --aspect 9:16 --quality h

# Square (1:1) or 4:5 for Instagram-style feeds
python scripts/generate.py "..." --aspect 1:1 --quality h
python scripts/generate.py "..." --aspect 4:5 --quality h

# Or fall back to the single-shot legacy generator
python scripts/generate.py "Explain Euler's identity" --simple
```

The final video is at `output/<run_id>/final.mp4`; on macOS it auto-opens
unless `--no-preview` is passed.
