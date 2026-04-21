# Pressing Analyst — Speaker Notes

## Slide 1 — Pressing Analyst (Title)
This presentation walks through the Pressing Analyst page of the TwelveGPT Educational app. The page converts pressing data from Twelve Football into natural-language coaching briefings using an LLM. Our focus is context engineering — not just prompting, but structuring the entire data pipeline so the model produces reliable, grounded output. The four pillars: pressing volume, disruption quality, resilience when bypassed, and engagement speed.

## Slide 2 — Bournemouth
Bournemouth is our first example because they represent an aggressive, high-volume pressing profile. On the left you can see all eight metrics with their z-score level. On the right is the LLM output — a four-sentence coaching briefing generated entirely from the structured data. This is what the coaching staff would read. Notice how the model identifies the trade-off: dominant territorial pressure but some vulnerability to line-breaking passes.

## Slide 3 — Fulham
Fulham is the neutral benchmark. They do not stand out in any pressing dimension, but their strength is behind the press — when opponents escape, they rarely score. This tests whether the system can describe a team that is unremarkable without inventing qualities that are not there. The LLM correctly identifies rest-defence resilience as the defining feature.

## Slide 4 — Ipswich Town
Ipswich is the fragile pressing case. The press is slow, easily bypassed, and offers minimal disruption. This example is important because a good system should describe weaknesses honestly without being unfairly negative. The model finds the one redeeming quality — low goals conceded after broken press — and frames it correctly as deeper damage absorption rather than pressing quality.

## Slide 5 — Step 1: Tell It Who It Is
This is the system prompt. We define the LLM as a tactical data analyst on a Premier League coaching staff. The key difference from Physical Analyst: Physical writes for recruitment departments about individual players; we write for the coaching room about entire teams. We also include a grounding pair that forces the model to say "football" rather than "soccer" — a small but important consistency detail.

## Slide 6 — Step 2: Tell It What It Knows
Before the model sees any team data, we teach it about pressing through 19 Q&A pairs. These cover metric definitions, metric combinations (e.g. "what does low PPDA plus high break rate mean?"), and interpretation rules. This is the same pattern as Physical Analyst's 49 Q&A pairs, but adapted for pressing-specific domain knowledge. The examples shown here are representative — the full set covers all eight metrics and their interactions.

## Slide 7 — Step 3: Tell It What Data to Use
This is the biggest structural difference from Physical Analyst. Physical uses word labels: "he was excellent in Speed." We go further and use full consequence sentences: "the team steps in early, allowing opponents very few passes before a defensive action." This eliminates directional ambiguity — the model never has to infer whether "poor" in a metric means opponents pass well or badly. We also pre-group metrics into Strengths, Neutral, and Weaknesses sections before the model sees them, and we use asymmetric thresholds: strengths require z > 1.0 but concerns surface earlier at z < −0.5.

## Slide 8 — Step 4, Example 1: Liverpool
On the left is the synthesized text that the model actually receives — structured into sections with metric names, values, ranks, and consequence sentences. On the right is our hand-written target output — the kind of four-sentence briefing we want the model to produce. Liverpool is the aggressive pressing example: high engagement, strong disruption, but exposed rest-defence.

## Slide 9 — Step 4, Example 2: Arsenal
Arsenal is the selective pressing example. They hold a high line but only engage at specific moments. This teaches the model that pressing intensity and defensive line height are not the same thing. The hand-written output demonstrates how to describe a team that presses well when it engages but does not do it often enough.

## Slide 10 — Step 4, Example 3: Nottingham
Nottingham is the weakest pressing profile in the set — the deepest block, the slowest engagement, the least disruption. This example teaches the model how to describe limitations without being harsh. The hand-written output correctly identifies rest-defence as the one genuine strength and frames the overall approach as a deliberate trade-off rather than a failure.

## Slide 11 — Step 4, Example 4: Wolverhampton
Wolverhampton is the neutral case — everything sits close to the league median. This is the hardest profile to describe well, because there is nothing dramatic to highlight. The hand-written output uses phrases like "close to the league norm" and "neither a weapon nor a liability." This teaches the model that neutral does not mean uninteresting — it means describing what the team chooses not to do.

## Slide 12 — The Pipeline
This is the end-to-end view. Raw pressing data flows through z-scoring, then into consequence sentences (not just labels), then into the layered prompt, and finally into the LLM. The key decisions box highlights the five things that distinguish this system from a naive prompt approach: consequence sentences instead of labels, pre-grouped sections, Block % as separate context, diverse few-shot examples, and grounded chat via RAG.

## Slide 13 — Bonus: Block Height Context
This is something Physical Analyst does not have. Block percentage tells the model where the team defends — high line or deep block — without treating it as a quality metric. This matters because the same pressing numbers mean different things depending on where the team sits. A deep team pressing poorly is making a deliberate choice; a high-line team pressing poorly has a structural problem. We load this from a separate CSV, mark it explicitly as "not a quality judgement," and demonstrate in all four few-shot examples how to integrate it naturally into the briefing.
