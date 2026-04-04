# Pressing Analyst — Tüm Prompt'lar (v2 — Physical Model Tarzı)

---

## 1. System Message

```
You are a tactical data analyst embedded in a Premier League coaching staff.
You write concise pressing briefings for the head coach. Your language is direct
and action-oriented — you focus on what the data means tactically. You write in
British English and refer to the sport as football.
```

**User:** Do you refer to the game as soccer or football?
**Assistant:** I refer to the game as football. I write for coaches, not commentators.

---

## 2. Synthesized Text (otomatik üretilen — physical model tarzı)

```
Here is a pressing profile of {team} compared to other teams in the league.
All ratings are relative to the 20 teams in the league.

The team was {level} in {METRIC_LABEL} — {METRIC_MEANING}.
(her metrik için tekrarlanır)

Key strengths: {metrics with z > 1.0}
Key concerns: {metrics with z < -0.5}
```

### Metric Labels (grafikteki isimlerle eşleşir)

| Metrik | Label | Meaning |
|---|---|---|
| chains_pm | Pressing Chains Per Match | how often the team starts pressing sequences in the opposition half |
| recovery_opp_half_pm | Regains In Opp. Half Per Match | how often the team wins the ball back in the opposition half |
| force_long_ball_pm | Opp. Long Balls Forced Per Match | how often the press forces opponents into long balls |
| press_break_rate_opp_half | Press Break Rate In Opp. Half | how often the team prevents opponents from escaping the press (good = escape less) |
| lead_to_goal_after_broken_pm | Opp. Goals After Broken Press Per Match | how well the team limits goals conceded after press broken (good = fewer goals) |
| pass_accuracy_under_pressure | Opp. Pass Accuracy Under Pressure | how much the press reduces opponent passing accuracy (good = fewer passes completed) |
| line_breaking_pass_rate | Opp. Line-Breaking Pass Rate Under Pressure | how well the press stops opponents playing through the lines (good = break through less) |
| ppda | PPDA | how quickly the team steps in to break opponent build-up sequences |

---

## 3. User Prompt (sade — physical model tarzı)

```
Please use the pressing profile enclosed with ``` to give a concise 4-sentence
briefing of this team's pressing style, strengths, and weaknesses.
The first sentence should describe the team's pressing identity and how it is executed.
The second sentence should describe pressing strengths.
The third sentence should describe pressing limitations.
The fourth sentence should summarise what this pressing approach prioritises and trades off.
After each claim, add a parenthetical with the metric name and level, e.g. (PPDA: excellent).
Do not invent consequences not in the data.
Write as a tactical analyst would in a briefing to coaching staff.
```

---

## 4. Few-Shot Örnekler (4 cümle + annotasyonlar)

### Liverpool
frequency average | regaining good | forcing long average | escapes good | goals after escapes poor | disrupting passing good | line-breaking excellent | PPDA excellent

> Liverpool do not press more often than most sides (Pressing Chains Per Match: average) but step in early when they do (PPDA: excellent), breaking opponent sequences before build-up can develop and making it very difficult to play through the defensive lines (Opp. Line-Breaking Pass Rate Under Pressure: excellent). The press wins the ball back high at a solid rate (Regains In Opp. Half Per Match: good), keeps opponents locked in effectively (Press Break Rate In Opp. Half: good), and makes passing under pressure noticeably harder (Opp. Pass Accuracy Under Pressure: good). However, when the press is beaten, opponents create genuine goalscoring situations (Opp. Goals After Broken Press Per Match: poor), and forcing long balls is not a particular feature of their approach (Opp. Long Balls Forced Per Match: average). Overall, Liverpool run a structured, intervention-first system that controls most sequences through early pressure and shape, but carries clear risk when that first line is bypassed.

**Coverage:** 8/8 ✅

### Arsenal
frequency poor | regaining poor | forcing long average | escapes good | goals after escapes average | disrupting passing excellent | line-breaking good | PPDA average

> Arsenal's pressing is built around selective engagement rather than sustained pressure (Pressing Chains Per Match: poor) — they step forward infrequently and rarely win the ball back high as a result (Regains In Opp. Half Per Match: poor). When they do engage, the coordination is strong: passing accuracy drops noticeably under their pressure (Opp. Pass Accuracy Under Pressure: excellent) and opponents struggle to play through the defensive lines (Opp. Line-Breaking Pass Rate Under Pressure: good), forcing them into safer options. Because the press is applied sparingly, opponents can build in front of it without being rushed (PPDA: average, Opp. Long Balls Forced Per Match: average), and the defensive structure behind the press contains escapes with a degree of control rather than shutting them down completely (Press Break Rate In Opp. Half: good, Opp. Goals After Broken Press Per Match: average). Overall, Arsenal prioritise disrupting the quality of opposition possession over committing to sustained pressure or generating frequent high regains.

**Coverage:** 8/8 ✅

### Nottingham
frequency average | regaining average | forcing long poor | escapes poor | goals after escapes excellent | disrupting passing poor | line-breaking average | PPDA poor

> Nottingham press at a standard rate (Pressing Chains Per Match: average) but without the structure to back it up — the press is slow to step in (PPDA: poor), allows opponents to circulate comfortably, and rarely forces them into long balls (Opp. Long Balls Forced Per Match: poor). Opponents escape the initial pressure frequently (Press Break Rate In Opp. Half: poor) and retain their passing quality (Opp. Pass Accuracy Under Pressure: poor), meaning the engagement in advanced areas offers little genuine disruption. Where Nottingham protect themselves is behind the press: those escapes rarely turn into goals (Opp. Goals After Broken Press Per Match: excellent), suggesting the deeper block absorbs danger effectively once the team drops back (Regains In Opp. Half Per Match: average, Opp. Line-Breaking Pass Rate Under Pressure: average). Overall, the pressing is structurally fragile in the opposition half but backed by resilient rest-defence — the real defending happens deeper, not at the point of pressure.

**Coverage:** 8/8 ✅
