# Give the correct gender words
def pronouns(gender):
    if gender.lower() == "male":
        subject_p, object_p, possessive_p = "he", "him", "his"
    else:
        subject_p, object_p, possessive_p = "she", "her", "her"

    return subject_p, object_p, possessive_p


# Describe the level of a metric in words
def describe_level(
    value,
    thresholds=[1.5, 1, 0.5, -0.5, -1],
    words=["outstanding", "excellent", "good", "average", "below average", "poor"],
):
    return describe(thresholds, words, value)


def describe(thresholds, words, value):
    """
    thresholds = lower bound of each word in descending order\n
    len(words) = len(thresholds) + 1
    """
    assert len(words) == len(thresholds) + 1, "Issue with thresholds and words"
    i = 0
    while i < len(thresholds) and value < thresholds[i]:
        i += 1

    return words[i]


# Format the metrics for display and descriptions
def format_metric(metric):
    if metric in ("Z_q", "Score"):
        return "Score"
    m = str(metric).strip()
    if m.lower() == "ppda (hb)":
        return "PPDA (HB)"
    if m.lower() == "ppda":
        return "PPDA"
    if m.lower() == "xt disruption":
        return "xT disruption"
    detailed_metric_labels = {
        "chains_pm": "Pressing Chains Per Match",
        "force_long_ball_pm": "Opp. Long Balls Forced Per Match",
        "recovery_opp_half_pm": "Regains In Opp. Half Per Match",
        "press_break_rate_opp_half": "Press Break Rate In Opp. Half",
        "lead_to_goal_after_broken_pm": "Opp. Goals After Broken Press Per Match",
        "pass_accuracy_under_pressure": "Opp. Pass Accuracy Under Pressure",
        "line_breaking_pass_rate_under_pressure": "Opp. Line-Breaking Pass Rate Under Pressure",
        "high_medium_block_pct": "% Out-of-Possession In High/Medium Block",
    }
    if m.lower() in detailed_metric_labels:
        return detailed_metric_labels[m.lower()]
    return (
        m.replace("_", " ")
        .replace(" adjusted per90", "")
        .replace("npxG", "non-penalty expected goals")
        .capitalize()
    )


def format_metric_value(metric, value):
    k = str(metric).strip().lower()
    v = float(value)

    if k == "high_medium_block_pct":
        return f"{v:.1f}%"
    if k in {
        "press_break_rate_opp_half",
        "pass_accuracy_under_pressure",
        "line_breaking_pass_rate_under_pressure",
    }:
        return f"{v * 100:.2f}%"
    if k in {
        "chains_pm",
        "force_long_ball_pm",
        "recovery_opp_half_pm",
        "lead_to_goal_after_broken_pm",
        "ppda",
        "ppda (hb)",
    }:
        return f"{v:.2f}"

    return f"{v:.2f}"


def write_out_metric(metric):
    return (
        metric.replace("_", " ")
        .replace("adjusted", "adjusted for possession")
        .replace("per90", "per 90")
        .replace("npxG", "non-penalty expected goals")
        + " minutes"
    )


def pressing_metric_short_label(metric: str) -> str:
    """Short plain-language label for the level-reference block in synthesized text."""
    labels = {
        "chains_pm": "Pressing Chains Per Match",
        "recovery_opp_half_pm": "Regains In Opp. Half Per Match",
        "force_long_ball_pm": "Opp. Long Balls Forced Per Match",
        "press_break_rate_opp_half": "Press Break Rate In Opp. Half",
        "lead_to_goal_after_broken_pm": "Opp. Goals After Broken Press Per Match",
        "pass_accuracy_under_pressure": "Opp. Pass Accuracy Under Pressure",
        "line_breaking_pass_rate_under_pressure": "Opp. Line-Breaking Pass Rate Under Pressure",
        "ppda": "PPDA",
    }
    k = str(metric).strip().lower()
    return labels.get(k, metric)


def pressing_metric_natural_clause(metric: str) -> str:
    """
    Football-language clause for wordalisation: avoids raw column names.
    Used after 'The team was <level> … compared to other teams in the league.'
    Only covers the eight metrics shown on the pressing analyst page.
    """
    k = str(metric).strip().lower()

    clauses = {
        "chains_pm": "when it came to how often they start pressing sequences in the opposition half",
        "recovery_opp_half_pm": "when it came to regaining the ball in the opposition half",
        "force_long_ball_pm": "when it came to forcing opponents to go long under pressure",
        "press_break_rate_opp_half": "when it came to keeping opponents locked in and stopping them from escaping the press in the opposition half (a higher level here means opponents escape less often)",
        "lead_to_goal_after_broken_pm": "when it came to reducing the damage after the press is broken (a higher level here means opponents score fewer goals after escaping — the team is better at containing the danger)",
        "pass_accuracy_under_pressure": "when it came to disrupting opponent passing accuracy under pressure (a higher level here means opponents complete fewer passes — the team's press makes passing harder for the opponent)",
        "line_breaking_pass_rate_under_pressure": "when it came to stopping opponents from playing through the defensive lines under pressure (a higher level here means opponents break through the lines less often — the team's pressing structure holds its shape better)",
        "ppda": "when it came to stepping in early to break opponent sequences before they can build in the opposition's 60%",
        "high_medium_block_pct": "when it came to how much of their out-of-possession time is spent defending in a high or medium block",
    }

    if k in clauses:
        return clauses[k]

    return "when it came to one aspect of how they press and defend without the ball"
