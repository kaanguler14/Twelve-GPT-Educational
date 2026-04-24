# CLAUDE.md

## Commands
- Run app: `streamlit run app.py`
- Embeddings rebuild: `python -m utils.build_embeddings`

## Design Decisions
- `PressingDescription.synthesize_text()` produces a narrative (profile → reward → risk → closing) rather than listed strengths/neutral/weaknesses. Metric values and ranks are not surfaced — only the consequence sentence from `METRIC_CONSEQUENCES` is used.
- Profile paragraph always contains `ppda` + `chains_pm` + `recovery_opp_half_pm` + block-context regardless of z-score (team identity — how often and how early they step in, and how much ball they actually win high). All three are defined in `PROFILE_METRICS`.
- Press-quality metrics (`pass_accuracy_under_pressure`, `force_long_ball_pm`, `line_breaking_pass_rate_under_pressure`, `press_break_rate_opp_half`) enter the reward paragraph if `z > 0.5` or the risk paragraph as "weaknesses" if `z < -0.5`. These describe what the press forces opponents to do — they are not "costs" because they reflect disruption quality, not a penalty paid for pressing.
- `lead_to_goal_after_broken_pm` (defined as `COST_METRIC`) is the only true cost: if `z > 0.5` (strong rest-defence) it enters reward; if `z < -0.5` (opponents score frequently when press is broken) it enters the risk paragraph as the "genuine cost".
- Metrics with z between -0.5 and 0.5 (outside profile) are dropped from the narrative.
- Risk paragraph concatenates an optional "The press struggles to disrupt opponents in other areas." weakness block and an optional "The genuine cost sits behind the press." cost block.
- Block-context sentence is threshold-based (3 variants) and contains no percentages or ranks.
- Closing cue picks one of six variants based on (reward, weakness, cost) counts. "Unforgiving when bypassed" is only used when `c > 0` (i.e., `lead_to_goal_after_broken_pm` is actually a negative), never purely from weakness metrics.
- The pressing description prompt (`PressingDescription.get_prompt_messages()`) tells the LLM to rewrite the briefing with connectives, cap output at 120 words, and preserve all facts without adding claims. The few-shot CSV (`data/gpt_examples/Pressing_analyst.csv`) contains only example pairs.
- `pressing_prompts_overview.md` is a design doc, not used in production. The actual prompts are in `classes/description.py` and `classes/chat.py`.
