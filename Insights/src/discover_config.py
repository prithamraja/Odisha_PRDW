import os

# Centralized model choice for Discover prose generation.
# Override via env var DISCOVER_PROSE_MODEL.
DISCOVER_PROSE_MODEL = os.getenv("DISCOVER_PROSE_MODEL", "gpt-5.5")

# The completion budget lives HERE, next to the model, because it is a property
# of the model and not of any one report.
#
# gpt-5.5 is a reasoning model: reasoning tokens are drawn from the same
# completion budget as the visible answer. phase5b_report was calling with
# max_completion_tokens=2000 -- ample for the previous mini model -- and on
# gpt-5.5 every one of those 2,000 tokens went to reasoning
# (completion_tokens_details.reasoning_tokens=2000, finish_reason='length'),
# so the API returned an empty string and the executive report was written with
# all nine per-view sections BLANK. Nothing failed loudly; the file was simply
# hollow.
#
# 9000 is the value phase5c_gamma_reports had already been carrying, and it is
# known-good for these prompts on this model. Keeping one constant means the
# next model swap cannot leave one report path silently under-budgeted while
# the others work.
DISCOVER_MAX_COMPLETION_TOKENS = int(
    os.getenv("DISCOVER_MAX_COMPLETION_TOKENS", "9000")
)
