"""Fictional study corpus.

Fictional on purpose: an agent that skips retrieval cannot answer
correctly from model memory, so evidence failures surface as visible
fabrication that the output judge also catches.
"""

STUDIES: dict[str, dict[str, str]] = {
    "T123": {
        "title": "Effects of compound ZX-14 on blood pressure in adults",
        "text": (
            "Study T123 was a 12-week randomized controlled trial of compound "
            "ZX-14 in 240 adults with stage-1 hypertension. Key findings: the "
            "treatment group showed a mean reduction in systolic blood pressure "
            "of 12 mmHg versus 3 mmHg for placebo. Mild dizziness was the most "
            "common adverse event, reported by 7 percent of participants."
        ),
    },
    "SL-88": {
        "title": "Compound RN-7 and sleep quality in shift workers",
        "text": (
            "Study SL-88 evaluated compound RN-7 in 120 shift workers over 8 "
            "weeks. Key findings: sleep onset latency improved by 22 percent "
            "versus baseline, and total sleep time increased by 41 minutes. "
            "No serious adverse events were reported."
        ),
    },
    "GI-4": {
        "title": "Dietary fiber blend FB-2 and gut microbiome diversity",
        "text": (
            "Study GI-4 tracked 90 participants taking fiber blend FB-2 for "
            "6 weeks. Key findings: microbiome diversity rose by 0.4 points on "
            "the Shannon index and self-reported bloating fell by 30 percent."
        ),
    },
}