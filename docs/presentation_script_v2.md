# Presentation Script v2 — Context Engineering: Pressing Analyst

> 18 slayt. Yeni slaytlar **[YENi]** ile isaretli.
> Her slayt icin: baslik, slayt icerigi, konusma metni.

---

## Slide 1 — Introduction

**Slayt icerigi:** Baslik, isimler, motivasyon cumlesi.

**Script:**
"Today we're presenting a system we call the Pressing Analyst. It analyses a team's pressing behaviour using data and automatically converts that data into meaningful, action-oriented text for coaching staff.

The project was developed by Kaan Guler, Hugo Vicente, and Sara Bentelli.

Our core motivation was straightforward: analysts produce enormous amounts of data, but coaches rarely have the time to work through it. We wanted to close that gap — turning numbers into decisions."

---

## Slide 2 — What Do We Want to Measure?

**Slayt icerigi:** Madde listesi (mevcut haliyle).

**Script:**
"We started by asking ourselves: what do we actually want to understand about pressing?

How aggressively does a team press in the opponent's half? Are opponents being forced into long, risky passes? Is the ball being won back through pressure? And critically — what happens when the press is broken?

One important detail: some of these metrics are inverted. For PPDA, pass accuracy under pressure, and press break rate, a *lower* number actually means *better* performance. Getting the direction wrong is one of the most common mistakes language models make when interpreting football data — so our system handles this explicitly from the start.

These questions shaped our framework around two dimensions: the *reward* of pressing and the *risk* of pressing."

---

## Slide 3 — Is Our Pressing a Wall or a Gamble?

**Slayt icerigi:** Mevcut haliyle.

**Script:**
"A strong press should do more than apply pressure. It should disrupt build-up, force rushed decisions, and win the ball high — while still keeping the team defensively organised behind it.

We framed this as a single question: *Is this press a wall or a gamble?*

That tension — between aggression and exposure — is exactly what our system measures and communicates."

---

## Slide 4 — Data to Text

**Slayt icerigi:** Mevcut tablo + **yeni not kutusu:**

> "Labelling uses symmetric z-score bands (outstanding ... poor).
> Grouping into Strengths / Weaknesses is **asymmetric by design**:
> strengths require z > 1.0, weaknesses surface at z < -0.5.
> Weaknesses are flagged earlier — a deliberate choice."

**Script:**
"At the core of the system are eight key metrics. For each one, we calculate a z-score — how many standard deviations a team sits from the league average.

We then map that score to a performance level: Poor, Below Average, Average, Good, Excellent, or Outstanding. Each level triggers a pre-written, contextually appropriate sentence. For example, if a team's PPDA z-score falls between 1.0 and 1.5, the system produces: 'The team steps in early, allowing opponents very few passes before a defensive action.'

But here's a critical design choice: when we group metrics into Strengths and Weaknesses, the thresholds are *not* symmetric. A metric only qualifies as a strength at z greater than 1.0, but weaknesses are flagged at z less than minus 0.5 — earlier, deliberately. In coaching, you want to catch problems before they become crises. This asymmetry reflects that philosophy.

Also — five of our eight metrics are inverted: lower raw values mean better performance. Instead of asking the model to figure out which direction is 'good', we solved this upstream. Each metric has a pre-written consequence sentence that already encodes the correct direction. The model never has to guess."

---

## Slide 5 — [YENi] Prompt Architecture

**Slayt icerigi:** Pipeline akis diyagrami:

```
Raw CSV Data
    |
    v
Z-Score Calculation (inverted metrics flipped)
    |
    v
Level Label (describe_level: outstanding ... poor)
    |
    v
Consequence Sentence (METRIC_CONSEQUENCES lookup)
    |
    v
Synthesize Text (Strengths / Neutral / Weaknesses + Context block)
    |
    v
4-Sentence Description Prompt
    |
    v
Few-Shot Examples (4 team profiles)
    |
    v
LLM (OpenAI API) --> Tactical Briefing
```

**Script:**
"Before we look at the prompts themselves, let's see the full pipeline.

Raw data enters as a CSV. We compute z-scores — flipping the sign for inverted metrics so that positive always means better. Each z-score maps to a level label via fixed thresholds. Each label triggers a pre-written consequence sentence.

These sentences are then grouped into Strengths, Neutral, and Weaknesses — using the asymmetric thresholds we just discussed — and assembled into a synthesized text block.

That text is wrapped with a specific 4-sentence description prompt, paired with four few-shot example outputs, and sent to the LLM.

The model never sees raw numbers or z-scores directly. It receives pre-interpreted, directionally correct, natural language — and its job is to synthesize that into a coaching briefing. This is the core of the context engineering: we do the analytical reasoning *before* the model, and let the model do what it's best at — writing."

---

## Slide 6 — System Prompt

**Slayt icerigi:** Mevcut system prompt + **yeni kutu:**

> **Terminology Alignment (few-shot trick):**
> User: "Do you refer to the game as soccer or football?"
> Assistant: "I refer to the game as football. I write for coaches, not commentators."

**Script:**
"To generate the text, we used the OpenAI API. But rather than simply prompting the model with data, we gave it a very specific identity — what we call a system prompt.

*'You are a tactical data analyst embedded in a Premier League coaching staff. You write concise pressing briefings for the head coach. Your language is direct and action-oriented. You write in British English and refer to the sport as football.'*

Why does this matter? Because the same data, given to a poorly configured model, can produce jargon-heavy, vague, or misleading output. The right identity definition pushes the model to a level a real coaching team could act on immediately.

We also used a small but effective alignment trick: a single question-answer exchange — 'Do you refer to the game as soccer or football?' — 'I refer to the game as football. I write for coaches, not commentators.' This locks in the terminology and the tone before any data is processed. One exchange, but it anchors the entire persona."

---

## Slide 7 — [YENi] Guardrails and Constraints

**Slayt icerigi:**

| Guardrail | Detail |
|-----------|--------|
| Asymmetric grouping | Strengths: z > 1.0 / Weaknesses: z < -0.5 |
| Anti-hallucination | "Do not invent consequences not in the data" |
| No jargon leakage | "Do not include metric names, level labels (e.g. excellent, poor), or parenthetical references" |
| Structured output | Exactly 4 sentences: identity, strengths, weaknesses, trade-off |
| Token limit | 250 tokens max |
| Inverse metrics | Direction resolved *before* the model via consequence sentences |

**Script:**
"Beyond the system prompt, we built a set of explicit guardrails into the description prompt.

First: the model is told to produce exactly four sentences. Sentence one describes the team's pressing identity. Sentence two covers strengths. Sentence three covers weaknesses — or, if there are none, average areas. Sentence four summarises the trade-off. This gives every briefing a consistent, predictable structure that coaching staff can rely on.

Second: anti-hallucination. The prompt explicitly says: *do not invent consequences not in the data.* If the synthesized text doesn't mention transition speed or possession recycling, the model must not fabricate them.

Third: no jargon leakage. The model is told not to include metric names, level labels like 'excellent' or 'poor', or parenthetical references. The output should read like a human analyst wrote it, not like a database dump.

Fourth: a 250-token limit keeps the output concise — a coach should be able to read it in under 30 seconds.

And finally: inverse metrics. PPDA, pass accuracy, press break rate — for all of these, lower is better. Instead of relying on the model to interpret direction correctly, we resolved it upstream. The consequence sentences already encode the correct meaning. The model's job is to write, not to reason about metric polarity."

---

## Slide 8 — Q&A Pairs and Context Enrichment

**Slayt icerigi:** Mevcut ornekler + **yeni alt baslik:**

> "These Q&A pairs serve a dual purpose:
> 1. Few-shot learning during description generation
> 2. RAG retrieval during live chat (embedded, top-5 semantic search)"

**Script:**
"We didn't stop at the system prompt. To teach the model genuine tactical understanding, we built a library of question-and-answer pairs.

For instance, we explicitly taught the model that a high Pressing Chains Per Match figure is not automatically a sign of effective pressing — it is a volume metric, not a quality metric. Without this nuance, the model might describe every high-volume pressing team as aggressive and effective — which is simply not accurate.

But these Q&A pairs serve a dual purpose. During description generation, they function as few-shot context — teaching the model how to reason about pressing. During the *live chat* phase — which we'll discuss in a moment — the same Q&A library is embedded and used for semantic retrieval. When a user asks a follow-up question, the system finds the five most relevant Q&A pairs and injects them into the conversation context.

So this is not just a static knowledge base — it's an active, searchable component that improves both the initial briefing and the interactive conversation."

---

## Slide 9 — Synthesize: Liverpool Case Study

**Slayt icerigi:** Mevcut Liverpool tablosu + **vurgu kutusu:**

> **Why is Context separate?**
> High/medium block % is not a quality metric — it's a tactical preference.
> It's shown separately so the model treats it as background, not as a strength or weakness.

**Script:**
"Let's make this concrete with Liverpool.

Why Liverpool? They are one of the most referenced teams in pressing literature — known for a high-intensity system, but also where the question of defensive exposure comes up regularly. That makes them an ideal test case.

Looking at the data, three clear layers emerge:

*Strengths:* PPDA ranks 3rd out of 20 — opponents are given very little time on the ball. The opponent line-breaking pass rate under pressure ranks 4th — the pressing structure holds its shape.

*Neutral:* Pressing chains and high regains are above average but not outstanding. Forcing long balls sits at a typical rate.

*Weakness:* When the press is broken, opponents score — Liverpool rank 16th out of 20. So no matter how well the press is applied, once it is beaten, the team is exposed.

Notice the Context block at the bottom: Liverpool spent 91.4% of their time in a high or medium block, ranking 10th. This is deliberately separated from Strengths and Weaknesses because block height is not a quality metric — it's a tactical preference. We explicitly tell the model: 'This is not a quality judgement — it reflects the team's defensive positioning preference.' This prevents the model from treating it as good or bad."

---

## Slide 10 — Few-Shot Examples: Liverpool Output + Strategy

**Slayt icerigi:** Liverpool uretilen metin (mevcut) + **yeni kutu:**

> **Few-shot strategy: 4 contrasting profiles**
> - Liverpool — aggressive press, weak rest-defence
> - Arsenal — selective press, low volume, high quality
> - Nottingham — deep block, fragile press, strong deep defence
> - Wolverhampton — entirely neutral baseline
>
> Each archetype teaches the model a different pressing identity.

**Script:**
"Given that data, the system produced the following briefing — you can read it on the slide.

The key point: a coach can read this before training and act on it immediately. No spreadsheets, no manual interpretation — just a clear tactical picture.

But this isn't the only example we gave the model. Our few-shot library contains four deliberately chosen profiles, each representing a different pressing archetype.

Liverpool: aggressive press with a weak rest-defence. Arsenal: selective, low-volume pressing with high engagement quality. Nottingham: deep block, fragile press upfield but excellent deep defence. And Wolverhampton: an entirely neutral profile — league average in every dimension.

This diversity is critical. If we had only shown aggressive pressing examples, the model would default to describing every team through that lens. By covering all four archetypes, we taught the model to recognise and articulate fundamentally different pressing identities."

---

## Slide 11 — Benchmark: Fulham

**Slayt icerigi:** Fulham grafigi + uretilen metin.

**Script:**
"We applied the system to all 20 Premier League teams. Each one received a visual profile and an automatically generated briefing.

Fulham press with a balanced footprint — neither aggressive nor passive. Their standout strength is limiting goals after the press is broken, but they struggle to force longer exits or disrupt passing under pressure."

---

## Slide 12 — Example: Bournemouth

**Slayt icerigi:** Bournemouth grafigi + uretilen metin.

**Script:**
"Bournemouth press at high intensity with a clear high-tempo approach. They win the ball back high and minimise build-up time, but trade off potential exposure behind the press for relentless disruption and quick recovery."

---

## Slide 13 — Example: Ipswich Town

**Slayt icerigi:** Ipswich grafigi + uretilen metin.

**Script:**
"Ipswich take a cautious, selective approach — starting sequences infrequently and conceding comfortable passing under pressure. They prioritise stability behind the press over aggressive engagement."

---

## Slide 14 — Example: Arsenal

**Slayt icerigi:** Arsenal grafigi + uretilen metin. **("Metin eklemek icin tiklayın" placeholder'ini temizle!)**

**Script:**
"Arsenal show perhaps the most interesting profile: selective but highly effective pressing. When they engage, passing under pressure becomes markedly harder and line-breaking is rare — but the low volume means they cannot dominate possession-based build-up across a full match.

Every team tells a different story. The system tells it consistently."

---

## Slide 15 — [YENi] Interactive Chat Pipeline (RAG)

**Slayt icerigi:** Akis diyagrami:

```
User Question
    |
    v
Embed Question (cosine similarity)
    |
    v
Top-5 Q&A Retrieval (from Pressing_analyst.parquet)
    +
Team Pressing Profile (cached synthesized text)
    |
    v
Chat System Prompt
("You are a tactical data analyst... provide 2-sentence answers.
 Do not deviate from the information provided.")
    |
    v
LLM (temperature = 0.3) --> Answer
```

> **Key design choices:**
> - temperature = 0.3 (factual, consistent output)
> - 2-sentence answer limit
> - "Do not deviate from this information" constraint
> - Same Q&A pairs used for both few-shot and retrieval

**Script:**
"The system doesn't stop at a one-time briefing. After the initial description is generated, the user enters an interactive chat where they can ask follow-up questions about the team's pressing.

Here's how it works: the user's question is embedded and compared against our Q&A library using cosine similarity. The five most relevant pairs are retrieved and injected into the prompt alongside the team's pressing profile.

The chat has its own system prompt — a tactical analyst identity similar to the description prompt, but with stricter constraints: answers are limited to two sentences, and the model is told explicitly not to deviate from the information provided.

We also set the temperature to 0.3 — much lower than the default. This is deliberate. In a coaching context, you want consistency and factual accuracy, not creative variation. The same question about the same team should produce essentially the same answer every time.

And notice: the same Q&A pairs that teach the model during description generation are reused here for retrieval. One knowledge base, two functions — few-shot learning and RAG search."

---

## Slide 16 — [YENi] Full System Architecture

**Slayt icerigi:** Buyuk akis diyagrami — her seyi birlestiren:

```
                          DATA LAYER
  pressing_detailed_metrics.csv --> PressingStats --> Z-scores + Ranks
                                                         |
                                                    PressingTeam
                                                   /            \
                                                  /              \
                          DESCRIPTION LAYER              CHAT LAYER
                     PressingDescription              PressingChat
                            |                              |
                     synthesize_text()              get_relevant_info()
                            |                         /          \
                     METRIC_CONSEQUENCES     Embedding Search   Cached synth text
                            |                    (top 5)              |
                     Synthesized Text               \              /
                            |                    Combined Context
                     4-Sentence Prompt                   |
                     + Few-Shot (x4)              Chat System Prompt
                            |                    (2-sentence, t=0.3)
                        LLM Call                       |
                            |                      LLM Call
                            v                          v
                    Tactical Briefing           Interactive Answer
```

**Script:**
"To bring it all together — here is the full system architecture.

On the left: the description layer. Raw data flows through z-scoring, consequence mapping, and synthesis into a structured prompt with four few-shot examples. The LLM produces a tactical briefing.

On the right: the chat layer. The same team profile is reused, augmented with retrieved Q&A pairs from an embedding search, and constrained by a stricter prompt with lower temperature.

Both sides share the same data source, the same consequence logic, and the same Q&A knowledge base. The difference is in how they use them: the description side uses few-shot examples to shape the style; the chat side uses semantic retrieval to find relevant context for specific questions.

This separation allows the briefing to be rich and narrative, while the chat stays precise and grounded."

---

## Slide 17 — Summary and Scalability

**Slayt icerigi:** 3 anahtar alan + olceklenebilirlik notu.

**Script:**
"To summarise, this system brings three layers together: data, context, and language.

We used the OpenAI API not just as a text generator, but as a tactical interpreter. What made that possible is context engineering — giving the model the right identity, the right constraints, the right background knowledge, the right examples, and the right retrieval system to reason from.

The system currently runs on Premier League data, but the architecture is fully scalable. Different leagues, different metrics, different languages — even a La Liga or Super Lig version — all achievable within the same framework.

Thank you for listening."

---

## Slide 18 — Ideas? Comments? Questions?

**Slayt icerigi:** Mevcut kapanıs slaytı.

---

# Degisiklik ozeti

| # | Degisiklik | Karsilik gelen geri bildirim |
|---|------------|------------------------------|
| 1 | Slide 2: Inverse metrik aciklamasi eklendi | Feedback #6 |
| 2 | Slide 4: Asimetrik esik notu + inverse metrik aciklamasi | Feedback #1, #6 |
| 3 | **Slide 5 [YENi]:** Prompt Architecture pipeline | Feedback #2 |
| 4 | Slide 6: Football/soccer alignment trick eklendi | Feedback #3 |
| 5 | **Slide 7 [YENi]:** Guardrails and Constraints (4-cumle yapisi, hallucination, token limiti) | Feedback #2 |
| 6 | Slide 8: Q&A'lerin RAG retrieval icin de kullanildigini belirt | Feedback #5 |
| 7 | Slide 9: Context blogunun neden ayri oldugunu acikla | Feedback #7 |
| 8 | Slide 10: 4 farkli few-shot profil stratejisi | Feedback #4 |
| 9 | **Slide 15 [YENi]:** Chat Pipeline (RAG, embedding, temperature) | Feedback #5 |
| 10 | **Slide 16 [YENi]:** Full System Architecture | Tum feedback birlestirmesi |
| 11 | Slide 14: Arsenal placeholder temizlenmeli | PDF duzeltme |
| 12 | Bos slide 11 (eski) kaldirildi; her takim kendi slaytinda | PDF duzeltme |
