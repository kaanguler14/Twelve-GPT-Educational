# Pressing Analyst — Metrics & Prompt Flow to the LLM (`docforslides`)

This document summarises how data is processed on the **Pressing Analyst** page, **how metrics are passed** to the model, and the **prompt-engineering** layers. It can serve as the single source for slide content.

**Related code:** `pages/pressing_analyst.py`, `classes/description.py` (`PressingDescription`), `classes/chat.py` (`PressingChat`), `classes/data_source.py` (`PressingStats`), `classes/embeddings.py` (`PressingEmbeddings`), `scripts/build_pressing_metrics.py`.

---

## 1. End-to-end flow (diagram)

```
pressing_detailed_metrics.csv
        │
        ▼
PressingStats.calculate_statistics(metrics, negative_metrics)
        │  → raw columns + {metric}_Z + {metric}_Ranks
        ▼
select_team() → PressingTeam (ser_metrics, relevant_metrics)
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
PressingDescription                    DistributionPlot (chart)
synthesize_text() + stream_gpt()            │
        │                                      │
        ▼                                      ▼
First assistant message (summary text)   Visual message
        │
        └──────────────► PressingChat (user questions)
                           get_relevant_info() = synthesize_text + embedding search
```

---

## 2. Data source and statistics layer

### 2.1 CSV and page constants

The page uses `data/pressing/pressing_detailed_metrics.csv`. The metric list is fixed in `pages/pressing_analyst.py`:

| Column (code) | Meaning in chart / text |
|-----------------|-------------------------|
| `chains_pm` | Pressing chains started in the opposition half per match (volume) |
| `recovery_opp_half_pm` | Ball recoveries in the opposition half per match |
| `force_long_ball_pm` | Long/high passes forced per match (opposition) |
| `press_break_rate_opp_half` | Broken pressing chains / total pressing chains in opp. half |
| `lead_to_goal_after_broken_pm` | Opposition goals per match after the press is broken |
| `pass_accuracy_under_pressure` | Opposition pass completion under pressure |
| `line_breaking_pass_rate_under_pressure` | Success rate on line-breaking passes under pressure (opposition) |
| `ppda` | Opp. completed passes in high block / meaningful pressing actions (lower = more aggressive) |

**Negative direction:** For the metrics below, *better performance* can mean numerically lower raw values; `PressingStats` **flips the sign** when building z-scores (`negative_metrics`) so “good = positive z” stays consistent:

- `ppda`, `press_break_rate_opp_half`, `lead_to_goal_after_broken_pm`, `pass_accuracy_under_pressure`, `line_breaking_pass_rate_under_pressure`

### 2.2 Z-score and level label

For each metric, `team.ser_metrics[metric + "_Z"]` is produced. For text, the level is mapped via `utils/sentences.describe_level(z)` to: outstanding, excellent, good, average, below average, poor.

---

## 3. “Giving metrics to the LLM”: `synthesize_text()`

**File:** `classes/description.py` — class `PressingDescription`.

The model does **not** see the raw table; it gets **natural language with locked-in direction**.

### 3.1 Two main mechanisms

1. **`METRIC_LABELS`** — Maps each internal column name to the same English label as the chart (e.g. `ppda` → `"PPDA"`).

2. **`METRIC_CONSEQUENCES`** — For each metric × level (outstanding … poor), a **single pitch-level consequence sentence**, so the model does not have to resolve “is high PPDA good or bad?”.

### 3.2 Structure of the generated text

- Opening: team name + league-relative profile (team count read from CSV row count).
- For each selected metric: **one consequence sentence** + **visible label** in parentheses — e.g. `… (PPDA)`.
- **Key strengths:** *label names* of metrics with z > 1.0 (comma-separated).
- **Key concerns:** *label names* of metrics with z < -0.5.

### 3.3 Optional context: high/medium block time

If `high_medium_block_pct` is present in `team.ser_metrics`, the text adds out-of-possession share in a high/medium block, league rank, and min–max–median. This is **not a quality judgement** — it describes positional preference. (If the column is missing from the CSV, this block is skipped.)

---

## 4. Prompt engineering: assembling messages

**Base class:** `Description.setup_messages()` (`classes/description.py`).

Order is fixed:

1. **`get_intro_messages()`** — For Pressing: system role (tactical data analyst on a Premier League staff, British English, “football”), short soccer/football exchange, then optional extra user/assistant opener if describe files exist.

2. **`data/describe/Pressing_analyst.csv`** — **Question–answer pairs** (metric definitions, commentary, league examples) as few-shot context so terminology stays consistent.

3. **`get_prompt_messages()`** — For Pressing: **four-sentence briefing** instructions; do not invent outcomes not in the data; **no metric names, level labels (excellent/poor), or parenthetical references** in the output; coaching-staff briefing tone.

4. **`data/gpt_examples/Pressing_analyst.csv`** — **Style few-shots** for the summary task (full scenarios such as Liverpool, Arsenal, Nottingham). First row: user instruction + short assistant reply; later rows: `Now do the same thing with the following: ```...``` ` with example profiles and target answers.

5. **Final user message (critical):**  
   `Now do the same thing with the following: ```{self.synthesized_text}````  
   So the **entire data summary** is passed to the model in **one fenced code block**.

**Streamlit expander:** Full message list under `Chat transcript` (debugging and teaching).

**Summary generation parameters (`pressing_analyst.py`):**  
`description.stream_gpt(stream=True, temperature=0.3)` — low temperature, repeatable briefing.

---

## 5. Chat mode: `PressingChat`

**Class:** `classes/chat.py` — `PressingChat`.

| Piece | Content |
|--------|--------|
| `instruction_messages()` | “UK-based football analyst”; user asks about pressing; messages arrive in a code block as `User: ...`; **2-sentence** answers; do not go beyond the supplied text. |
| `get_relevant_info()` | First `PressingDescription.synthesize_text()` (current team summary), then **embedding search** on `data/embeddings/Pressing_analyst.parquet` (top 5 Q&A rows). |
| `handle_input()` | Before the user question: `Here is the relevant information...` + `\`\`\`User: {input}\`\`\`. |

**Temperature:** `handle_input(..., temperature=0.3, stream=True)` — aligned with the summary.

---

## 6. Embedding dataset

- **File:** `data/embeddings/Pressing_analyst.parquet`  
- **Build:** Embeddings from CSVs via `pages/embedder.py` (same pattern as Football Scout).
- **Use:** Q&A pairs selected by cosine similarity to the user query, combining **general pressing knowledge** with the **team-specific synthesised text** in chat.

---

## 7. Building raw metrics (reference)

`scripts/build_pressing_metrics.py` builds `pressing_detailed_metrics.csv` from dynamic event data: PPDA zone threshold, pressing chain summaries, forced long balls, broken press, goals, etc. For a “metric definitions” slide, use this script together with explanations in `data/describe/Pressing_analyst.csv`.

---

## 8. Short “elevator pitch” bullets for slides

- Metrics are **normalised within the league**; copy uses **direction-locked consequence sentences**.
- Prompt is **layered:** role → describe Q&A → task → gpt_examples → **single-block team summary**.
- Chat **re-injects** the same summary and adds **FAQ-style depth** via embeddings; system instructions **ground** the model and limit hallucinations.

---

## 9. Note on `pressing_prompts_overview.md`

The repo file `pressing_prompts_overview.md` may contain an early design sketch. **Production behaviour** (`PressingDescription.get_prompt_messages`) **forbids parenthetical metric references** in the model output; few-shot examples use plain tactical prose. When updating slides or docs, treat **strings in `classes/description.py`** as the source of truth.

---

*TwelveGPT Educational — Pressing Analyst documentation (docforslides).*
