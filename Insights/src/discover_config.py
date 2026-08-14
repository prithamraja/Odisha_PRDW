import os

# Centralized model choice for Discover prose generation.
# Override via env var DISCOVER_PROSE_MODEL.
#
# D17 pins GPT-5.6. Verified against the LIVE model list on 2026-08-14 rather
# than guessed, and the list had a surprise in it: there is no plain `gpt-5.6`.
# GPT-5.6 ships as three ids -- `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`
# -- created within eleven minutes of each other and carrying no distinguishing
# metadata beyond the name. So the pin had to be made on evidence.
#
# All three were probed with the same real phase5b prompt (view2, 15 findings,
# 9,049 prompt tokens) at the budget below. All three returned non-empty prose
# with finish_reason='stop' and wide headroom:
#
#     luna   reasoning 1,024  visible   987  headroom 6,989 of 9,000
#     sol    reasoning 1,565  visible 1,057  headroom 6,378 of 9,000
#     terra  reasoning   512  visible 1,007  headroom 7,481 of 9,000
#
# Budget safety therefore does not separate them. The prose did. `terra`
# misattributed the section's headline figure, writing "across those five
# years, it recorded 2,135 vouchers" for a total that spans all six; `sol` was
# the only one of the three to scope that figure correctly AND to apply the
# recorded-zero rule unprompted ("the data cannot establish whether no linked
# expenditure occurred or whether it was not entered as linked expenditure").
# That is exactly the class of error the calibration gate exists to catch, so
# `sol` is the pin. The operator can flip to either sibling with the env var,
# with no code change and no re-run of anything upstream.
DISCOVER_PROSE_MODEL = os.getenv("DISCOVER_PROSE_MODEL", "gpt-5.6-sol")

# The completion budget lives HERE, next to the model, because it is a property
# of the model and not of any one report.
#
# These are reasoning models: reasoning tokens are drawn from the same
# completion budget as the visible answer. phase5b_report was calling with
# max_completion_tokens=2000 -- ample for the previous mini model -- and on
# gpt-5.5 every one of those 2,000 tokens went to reasoning
# (completion_tokens_details.reasoning_tokens=2000, finish_reason='length'),
# so the API returned an empty string and the executive report was written with
# all nine per-view sections BLANK. Nothing failed loudly; the file was simply
# hollow.
#
# 9000 was carried over from gpt-5.5 and is RE-VERIFIED for 5.6 by the probe
# above: the worst case of the three left 6,378 tokens unspent, so the constant
# is not raised. Keeping one constant means the next model swap cannot leave one
# report path silently under-budgeted while the others work.
DISCOVER_MAX_COMPLETION_TOKENS = int(
    os.getenv("DISCOVER_MAX_COMPLETION_TOKENS", "9000")
)
