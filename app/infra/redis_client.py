"""Redis adapter — short-term conversation state + cache.

Per the brief, TTLs are explicit and justified (value + reasoning recorded in
DECISIONS.md D13, behavior at the TTL boundary documented). Services own cache
invalidation; this adapter only provides the primitives.
"""

# TODO: redis.asyncio client from Vault-resolved password
# TODO: get/set conversation state with explicit TTL constant
# TODO: cache helpers

SHORT_TERM_TTL_SECONDS = 0  # TODO: set + justify in DECISIONS.md (must not stay 0)
