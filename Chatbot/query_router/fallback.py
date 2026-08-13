FALLBACK_EXAMPLES: dict[str, list[str]] = {
    "A single farmer": [
        "What is the PM-KISAN record for Ramesh Naidu?",
        "What are the total benefits for Lakshmi Devi across every scheme?",
        "Which datasets is Suresh Reddy present in?",
        "What did MARKFED procure from Mohan Rao, and was payment made?",
    ],
    "Coverage & subsidy": [
        "How many PM-KISAN beneficiaries are there in each mandal of Krishna district?",
        "How much input subsidy went to each mandal of Guntur district?",
        "What is the micro-irrigation coverage in each mandal of Kurnool district?",
        "Which mandals in Krishna district have the biggest eKYC backlog?",
    ],
    "Procurement & payments": [
        "How much was procured in each mandal of Guntur district?",
        "Which farmers in Krishna district are still unpaid for procurement?",
        "How much DBT was credited in each mandal of Prakasam district?",
        "Which sanctions are stalled in Anantapur district?",
    ],
    "Targeting & data quality": [
        "Give me the social category breakdown for Krishna district.",
        "What is the male-female split in Guntur district?",
        "Which farmers in Krishna district show a land discrepancy?",
        "Are there any malformed Aadhaar numbers in our systems?",
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
