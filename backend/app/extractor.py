import re

from app.llm import redact_secrets
from app.models import CandidateFact, ExtractionResult

LOCAL_SENSITIVE_PATTERNS = (
    (
        "health",
        "high",
        "health",
        re.compile(
            r"\b(?:doctor|therapy|therapist|anxiety|adhd|diagnos(?:ed|is)?|"
            r"medication|medicine|prescription|medical|surgery|symptom|illness)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "finance",
        "high",
        "finance",
        re.compile(
            r"\b(?:bank account|credit score|debt|loan|mortgage|income|"
            r"bank balance|financial hardship|credit card)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "job_search",
        "high",
        "personal",
        re.compile(
            r"\b(?:job hunting|looking for a new job|job search|"
            r"interviewing at other companies|salary negotiation)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "relationship",
        "high",
        "personal",
        re.compile(
            r"\b(?:my partner|my spouse|my marriage|my breakup|"
            r"getting divorced|my divorce|relationship problems)\b",
            re.IGNORECASE,
        ),
    ),
)


def _local_sensitive_facts(message, zone):
    """Detect sensitive sentences locally.

    The sentence becomes a pending fact (always asked about). It is hidden from
    Claude unless the user is already chatting in the zone it belongs to, e.g.
    health details stay visible to Claude in the Health zone so it can help.
    """
    facts = []
    redacted = message
    for category, sensitivity, suggested_zone, pattern in LOCAL_SENSITIVE_PATTERNS:
        match = pattern.search(redacted)
        if not match:
            continue
        start, end = _sentence_bounds(redacted, match.start(), match.end())
        original = redacted[start:end].strip()
        if not original:
            continue
        facts.append(
            CandidateFact(
                content=f"User shared a private {category.replace('_', ' ')} detail: {original}",
                short=f"{category.replace('_', ' ')} detail",
                category=category,
                sensitivity=sensitivity,
                confidence=0.9,
                suggested_zone=suggested_zone,
            )
        )
        if zone != suggested_zone:
            redacted = (
                redacted[:start]
                + "[private detail withheld until you approve]"
                + redacted[end:]
            )
    return redacted, facts


def _sentence_bounds(message, start, end):
    left = 0
    for boundary in re.finditer(r"[.!?](?:\s+|$)", message[:start]):
        prefix = message[: boundary.start()].rstrip().casefold()
        if boundary.group(0).startswith(".") and prefix.endswith(
            ("dr", "mr", "mrs", "ms", "prof")
        ):
            continue
        left = boundary.end()

    right = len(message)
    for boundary in re.finditer(r"[.!?](?:\s+|$)", message[end:]):
        prefix = message[end : end + boundary.start()].rstrip().casefold()
        if boundary.group(0).startswith(".") and prefix.endswith(
            ("dr", "mr", "mrs", "ms", "prof")
        ):
            continue
        right = end + boundary.end()
        break
    return left, right


def _explicit_command(message):
    lower = message.casefold()
    if re.search(r"\b(?:don't|do not) remember\b|\boff the record\b", lower):
        return "dont_remember", None
    if match := re.search(r"\bforget\s+(.+)", message, re.IGNORECASE):
        return "forget", match.group(1).strip(" .!?")
    if re.search(r"\b(?:remember this|save that|keep this in mind)\b", lower):
        return "remember", None
    if re.search(r"\b(?:just for this|use it once)\b", lower):
        return "use_once", None
    match = re.search(
        r"\bkeep this in (health|work|finance|personal) only\b", lower
    )
    if match:
        return f"zone_only:{match.group(1)}", None
    return "none", None


def extract(llm, message, zone, history):
    """Returns (text that is safe to store and send to Claude, extraction result)."""
    safe_message, sensitive_facts = _local_sensitive_facts(message, zone)
    safe_message, secrets = redact_secrets(safe_message)
    result = llm.extract(safe_message, zone, history)
    command, target = _explicit_command(message)
    # Local detection is a safety net: only add it when Claude didn't already
    # report a fact of the same sensitive category.
    model_categories = {fact.category for fact in result.facts}
    local = [fact for fact in sensitive_facts if fact.category not in model_categories]
    return safe_message, ExtractionResult(
        command=command if command != "none" else result.command,
        command_target=target if command == "forget" else result.command_target,
        facts=[*result.facts, *local, *secrets],
    )
