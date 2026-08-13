"""What the bot offers when nothing in the catalogue matches.

The examples are grouped the way an officer's work is, not the way the catalogue
is: what did GPs plan, what did they spend, what is stuck, and what does the data
itself not support. Each line is phrased as a real question and routes cleanly
through the ordinary matcher, so a user can copy one verbatim and get an answer.
"""
FALLBACK_EXAMPLES: dict[str, list[str]] = {
    "Planning (GPDP)": [
        "How many Gram Panchayats in Khordha uploaded their GPDP in 2024-2025?",
        "Which Gram Panchayats have not yet uploaded their GPDP?",
        "What percentage of Gram Panchayats in each block have uploaded their GPDP?",
        "Which focus area has the highest number of planned activities?",
    ],
    "Budget & expenditure": [
        "What is the total actual expenditure in 2024-2025?",
        "What percentage of the planned expenditure has been utilised?",
        "How much expenditure was incurred under each funding source?",
        "How much funding is sanctioned under tied and untied components?",
    ],
    "Progress, approvals & assets": [
        "How many activities are still awaiting administrative approval?",
        "What is the completion rate under each theme?",
        "Which activities are abandoned, and what did they cost?",
        "How many assets were created in Barpali block this year?",
    ],
    "Sanitation (SBM)": [
        "How many Individual Household Latrines have been planned in 2024-2025?",
        "How many community compost pits have been completed?",
        "What is the expenditure on Solid Waste Management activities?",
    ],
    "Alerts & data quality": [
        "Which Gram Panchayats recorded no activity in 2024-2025?",
        "Which activities are marked completed but have no expenditure recorded?",
        "How many activities have no focus area recorded?",
    ],
}


def generate_fallback_message(dashboard_questions: dict[str, str]) -> str:
    lines = [
        "I'm not sure I can answer that specific question yet.\n",
        "Here are some things I can help with:\n",
    ]
    for category, examples in FALLBACK_EXAMPLES.items():
        lines.append(f"**{category}**")
        for ex in examples[:2]:
            lines.append(f"  • {ex}")

    return "\n".join(lines)
