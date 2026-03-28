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
    if m.lower() == "xt disruption":
        return "xT disruption"
    return (
        m.replace("_", " ")
        .replace(" adjusted per90", "")
        .replace("npxG", "non-penalty expected goals")
        .capitalize()
    )


def write_out_metric(metric):
    return (
        metric.replace("_", " ")
        .replace("adjusted", "adjusted for possession")
        .replace("per90", "per 90")
        .replace("npxG", "non-penalty expected goals")
        + " minutes"
    )


def pressing_metric_natural_clause(metric: str) -> str:
    """
    Football-language clause for wordalisation: avoids raw column names (recovery, PPDA, xT, etc.).
    Used after 'The team was <level> … compared to other teams in the league.'
    """
    k = str(metric).strip().lower()
    aliases = {
        "regains/match": "recovery",
        "long ball delta": "force long ball",
        "xt disruption %": "xt disruption",
        "opp pass%(d3,hb)": "opp_pass_d3_hb",
        "shots/regain/m": "lead to shot",
        "z_q": "score",
    }
    k = aliases.get(k, k)

    clauses = {
        "recovery": "when it came to regaining the ball during the press",
        "force long ball": "when it came to forcing opponents to play long",
        "xt disruption": "when it came to disrupting the opponent's threat during buildup",
        "lead to shot": "when it came to turning pressing moments into shooting opportunities",
        "danger": "when it came to how dangerous the situations they allow while pressing are",
        "beaten": "when it came to how often they are bypassed by the first pass under pressure",
        "ppda (hb)": "when it came to how aggressively they hunt the ball in the high block",
        "ppda": "when it came to how aggressively they press relative to opponent passing",
        "bypass %": "when it came to how easily opponents play through their press",
        "danger %": "when it came to how dangerous the situations they allow while pressing are",
        "beaten %": "when it came to how often they are bypassed by the first pass under pressure",
        "block %": "when it came to how often they block or cut out passes in the press",
        "score": "when it came to overall pressing impact as a whole",
        "z_q": "when it came to overall pressing impact as a whole",
        "chains/match": "when it came to how often pressing sequences start",
        "opp_pass_d3_hb": "when it came to opponent passing in deep areas against their high block",
    }

    if k in clauses:
        return clauses[k]

    return "when it came to one aspect of how they press and defend without the ball"
