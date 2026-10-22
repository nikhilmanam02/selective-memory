from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import CandidateFact

SENSITIVE_CATEGORIES = {"health", "finance", "job_search"}
VALID_ZONES = {"global", "personal", "work", "health", "finance"}


@dataclass(frozen=True)
class Decision:
    action: str
    rule: Optional[str] = None
    zone: Optional[str] = None
    expires_in_hours: Optional[int] = None
    reason: str = ""
    learned: bool = False


def decide(
    fact: CandidateFact, current_zone: str, learned: dict, command: str = "none"
) -> Decision:
    if command == "dont_remember":
        return Decision("IGNORE", reason="You asked me not to remember this.")
    if command == "forget":
        return Decision("IGNORE", reason="You asked me to forget matching information.")
    if command == "use_once":
        return Decision("USE_ONCE", "one_time", current_zone, reason="You asked me to use this once.")
    if command == "remember":
        sensitive = fact.category in SENSITIVE_CATEGORIES or fact.sensitivity == "high"
        zone = current_zone if sensitive else "global"
        rule = "zone_only" if sensitive else "forever"
        return Decision("AUTO_SAVE", rule, zone, reason="You explicitly asked me to remember this.")
    if isinstance(command, str) and command.startswith("zone_only:"):
        target = command.split(":", 1)[1]
        if target in VALID_ZONES - {"global"}:
            return Decision("AUTO_SAVE", "zone_only", target, reason=f"You asked me to keep this in {target.title()} only.")

    if not fact.is_about_user:
        return Decision("IGNORE", reason="This doesn't appear to be a fact about you.")
    if fact.category == "secret":
        return Decision("USE_ONCE", "one_time", current_zone, reason="Secrets are used once, then deleted.")

    preference = learned.get(fact.category)
    if preference:
        behavior = preference.get("behavior")
        zone = preference.get("zone") or current_zone
        if behavior == "never":
            return Decision("IGNORE", reason=f"You asked me not to remember {fact.category} information.", learned=True)
        if behavior == "ask":
            return Decision("ASK", zone=zone, reason="You prefer that I ask before saving this information.", learned=True)
        if behavior == "use_once":
            return Decision("USE_ONCE", "one_time", zone, reason="Your usual choice is to use this once.", learned=True)
        if behavior == "auto_forever":
            return Decision("AUTO_SAVE", "forever", "global", reason="Saved using your usual choice.", learned=True)
        if behavior == "zone_only":
            return Decision("AUTO_SAVE", "zone_only", zone, reason=f"Saved to {zone.title()} using your usual choice.", learned=True)
        if behavior == "session":
            return Decision("AUTO_SAVE", "session", zone, reason="Saved for this chat using your usual choice.", learned=True)

    if fact.category in SENSITIVE_CATEGORIES or (
        fact.category == "relationship" and fact.sensitivity == "high"
    ):
        zone = fact.suggested_zone
        if zone == "global":
            zone = current_zone
        return Decision("ASK", zone=zone, reason=f"{fact.category.replace('_', ' ').title()} information is sensitive, so I'm asking first.")
    if fact.confidence < 0.6:
        return Decision("ASK", zone=fact.suggested_zone, reason="I'm not sure I understood this as a lasting fact, so I'm asking first.")
    if fact.is_temporary:
        hours = max(1, min(fact.expires_in_hours or 72, 720))
        return Decision("AUTO_TEMPORARY", "temporary", fact.suggested_zone, hours, "This sounds time-limited, so I'll forget it automatically.")
    if fact.sensitivity in {"low", "medium"}:
        if fact.category == "work":
            return Decision("AUTO_SAVE", "zone_only", "work", reason="Work details stay in your Work zone.")
        return Decision("AUTO_SAVE", "forever", "global", reason="Simple personal context is safe to remember.")
    return Decision("ASK", zone=fact.suggested_zone, reason="This may be sensitive, so I'm asking before saving.")
