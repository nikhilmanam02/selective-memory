import logging
import re
from typing import Protocol

from anthropic import Anthropic

from app.config import settings
from app.models import AnswerResult, CandidateFact, ExtractionResult

logger = logging.getLogger(__name__)

SECRET_PATTERNS = (
    ("Card number", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("Social security number", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("Password", re.compile(r"password\s+is\s+(\S+)", re.IGNORECASE)),
    ("Access code", re.compile(r"\b(?:code|pin)\s+is\s+(\d{4,8})\b", re.IGNORECASE)),
)


class LLM(Protocol):
    def extract(self, message: str, zone: str, history: list[dict]) -> ExtractionResult: ...

    def answer(
        self,
        message: str,
        zone: str,
        allowed: list[dict],
        withheld_counts: dict,
        history: list[dict],
    ) -> AnswerResult: ...


def redact_secrets(message):
    redacted = message
    found = []
    for label, pattern in SECRET_PATTERNS:
        for match in list(pattern.finditer(redacted)):
            value = match.group(1) if match.lastindex else match.group(0)
            if not value or value == "[private detail]":
                continue
            content = f"User provided a {label.lower()} for this task"
            found.append(
                CandidateFact(
                    content=content,
                    short=label,
                    category="secret",
                    sensitivity="high",
                    confidence=1.0,
                    suggested_zone="personal",
                    sensitive_span=value,
                )
            )
            redacted = redacted.replace(match.group(0), "[private detail]", 1)
    return redacted, found


class MockLLM:
    """Deterministic stand-in for Claude, used by the automated tests only."""

    def extract(self, message, zone, history):
        lower = message.lower()
        command = "none"
        target = None
        if re.search(r"\b(?:don't|do not) remember\b|\boff the record\b", lower):
            command = "dont_remember"
        elif match := re.search(r"\bforget\s+(.+)", message, re.IGNORECASE):
            command, target = "forget", match.group(1).strip(" .!?")
        elif re.search(r"\b(?:remember this|save that|keep this in mind)\b", lower):
            command = "remember"
        elif re.search(r"\b(?:just for this|use it once)\b", lower):
            command = "use_once"
        elif match := re.search(
            r"\bkeep this in (health|work|finance|personal) only\b", lower
        ):
            command = f"zone_only:{match.group(1)}"

        if command in {"forget", "dont_remember"}:
            return ExtractionResult(command=command, command_target=target)

        if lower.strip().endswith("?") and not re.search(
            r"\b(?:i am|i'm|i have|i love|i like|i prefer|i work|my \w+ is)\b", lower
        ):
            return ExtractionResult(command=command, command_target=target)

        facts = []
        uncertain = bool(re.search(r"\b(?:maybe|i think|might|joking)\b", lower))
        confidence = 0.4 if uncertain else 0.9

        relationship = re.search(
            r"\bmy (sister|brother|mom|mother|dad|father|partner|friend) is (\w+)",
            message,
            re.IGNORECASE,
        )
        if relationship:
            label = relationship.group(1).lower()
            facts.append(
                CandidateFact(
                    content=f"User's {label} is {relationship.group(2)}",
                    short=f"{label}’s name",
                    category="relationship",
                    sensitivity="low",
                    confidence=confidence,
                )
            )

        if re.search(r"\b(?:doctor|therapy|therapist|anxiety|adhd|diagnos|medication|appointment)\b", lower):
            phrase = message.strip().rstrip(".")
            facts.append(
                CandidateFact(
                    content=f"User {phrase[0].lower() + phrase[1:]}",
                    short="health detail",
                    category="health",
                    sensitivity="high",
                    confidence=confidence,
                    suggested_zone="health",
                )
            )

        if re.search(r"\b(?:interview|job hunting|looking for a new job|salary)\b", lower):
            facts.append(
                CandidateFact(
                    content=f"User {message.strip().rstrip('.')}",
                    short="job search",
                    category="job_search",
                    sensitivity="high",
                    confidence=confidence,
                    suggested_zone="personal",
                )
            )

        if match := re.search(r"\bi work (?:at|as)\s+(.+)", message, re.IGNORECASE):
            facts.append(
                CandidateFact(
                    content=f"User works {message[match.start() + 2:].strip().rstrip('.')}",
                    short="work details",
                    category="work",
                    sensitivity="medium",
                    confidence=confidence,
                    suggested_zone="work",
                )
            )

        location = re.search(
            r"\b(?:i'm|i am) in ([A-Z][\w-]+)(?:\s+(?:until|this week|for))?",
            message,
            re.IGNORECASE,
        )
        if location and re.search(r"\b(?:this week|until|visiting)\b", lower):
            facts.append(
                CandidateFact(
                    content=f"User is in {location.group(1)} temporarily",
                    short=f"{location.group(1)} trip",
                    category="location",
                    sensitivity="medium",
                    confidence=confidence,
                    is_temporary=True,
                    expires_in_hours=72,
                    suggested_zone=zone,
                )
            )

        if re.search(r"\b(?:vegetarian|vegan|i like|i love|i prefer|window seat|spicy food)\b", lower):
            phrase = message.strip().rstrip(".")
            parts = re.split(r"\s+and\s+(?=(?:i |I |my ))", phrase)
            for part in parts:
                part_lower = part.lower()
                if not re.search(
                    r"\b(?:vegetarian|vegan|i like|i love|i prefer|window seat|spicy food)\b",
                    part_lower,
                ):
                    continue
                clean = re.sub(r"^(?:and\s+)?", "", part, flags=re.IGNORECASE).strip()
                content = clean[0].upper() + clean[1:] if clean else phrase
                facts.append(
                    CandidateFact(
                        content=f"User {content[0].lower() + content[1:]}",
                        short=self._preference_short(clean),
                        category="preference",
                        sensitivity="low",
                        confidence=confidence,
                    )
                )

        unique = {}
        for fact in facts:
            unique[fact.content.casefold()] = fact
        return ExtractionResult(command=command, command_target=target, facts=list(unique.values()))

    @staticmethod
    def _preference_short(text):
        words = re.sub(r"^(i |always |really )+", "", text, flags=re.IGNORECASE).split()
        return " ".join(words[-3:]).strip(" .,!").lower() or "preference"

    def answer(self, message, zone, allowed, withheld_counts, history):
        lower = message.lower()
        relevant = []
        keys = {
            "dinner": {"preference", "health"},
            "food": {"preference", "health"},
            "eat": {"preference", "health"},
            "meal": {"preference", "health"},
            "email": {"work"},
            "manager": {"work"},
            "friday off": {"schedule", "work"},
            "trip": {"location"},
            "seattle": {"location"},
            "what do you know": set(),
        }
        categories = set()
        for keyword, matched_categories in keys.items():
            if keyword in lower:
                categories.update(matched_categories)
        for memory in allowed:
            content_lower = memory["content"].lower()
            if memory["category"] in categories or any(
                token in lower for token in content_lower.split() if len(token) > 4
            ):
                relevant.append(memory)

        ids = [memory["id"] for memory in relevant]
        if re.search(r"\b(?:card number|password|pin|code)\b", lower):
            text = "I don't have that. Any one-time detail was deleted after its task."
        elif "dinner" in lower or "food" in lower or "eat" in lower:
            details = [memory["content"].replace("User ", "").lower() for memory in relevant]
            text = "Here’s a dinner idea that fits"
            text += f" what you’ve shared: {', '.join(details)}." if details else "—what kind of food sounds good?"
        elif "email" in lower or "manager" in lower:
            text = "Here’s a professional draft:\n\nHi, I’d like to ask about taking Friday off. Please let me know if that works for the team. Thank you."
        elif re.search(r"\b(?:diagnosed|health|medication|therapy)\b", lower) and not relevant:
            text = "I don't have that information available in this zone."
        elif re.search(r"\b(?:what do you know|what do you remember)\b", lower):
            text = "I can use the memories available in this zone. You can review or delete them in the Memory dashboard."
        elif relevant:
            text = "I’ll keep that context in mind: " + "; ".join(item["content"] for item in relevant) + "."
        else:
            text = "I’m here to help. What would you like to work on?"
        return AnswerResult(text=text, used_memory_ids=ids)


CATEGORY_VALUES = [
    "preference", "identity", "relationship", "schedule", "location", "work",
    "health", "finance", "secret", "job_search", "other",
]
ZONE_VALUES = ["global", "personal", "work", "health", "finance"]

EXTRACT_SYSTEM = """You read the user's latest message and extract lasting facts about THE USER
for a personal assistant's memory, plus any explicit memory command.

Commands (set "command"):
- "remember this", "save that", "keep this in mind" -> remember
- "don't remember this", "don't save this", "off the record" -> dont_remember
- "forget X", "delete what I said about X" -> forget, with command_target = X
- "just for this", "use it once" -> use_once
- "keep this in health/work/finance/personal only" -> zone_only:<zone>
Otherwise command = "none".

Facts:
- Only facts about the user: preferences, identity, relationships, schedule, location,
  work, health, finance, job search. Never questions, requests, or facts about the world.
- content: third person, short and grammatical ("User is vegetarian").
- short: 1-4 word label for a UI chip ("vegetarian").
- sensitivity: low (tastes, hobbies, names), medium (location, employer, schedule),
  high (health, money, job search, intimate relationships, anything embarrassing).
- confidence 0-1: how sure you are this is a true, lasting fact. Jokes, hypotheticals,
  maybes, or facts about other people -> below 0.6.
- is_temporary + expires_in_hours for time-bound facts (trips, "this week", "until Friday").
- suggested_zone: global for general preferences/identity; else personal|work|health|finance.
  The current zone is {zone}; prefer it when unsure.
- Text like [private detail] has already been removed for privacy; ignore it.
Return an empty facts list for small talk, greetings, and pure questions."""

ANSWER_SYSTEM = """You are a warm, concise personal assistant. Current zone: {zone}.
You may ONLY use these memories about the user:
{memories}
Other zones hold memories you cannot see (counts only): {hidden}.
Rules:
- Use memories naturally when they help; don't recite them unless asked.
- For recommendations (food, places, products, plans), only suggest options that fit
  EVERY relevant memory at once (e.g. vegetarian AND Japanese), and say in one short
  phrase which preferences you applied.
- Never invent personal facts that are not listed.
- If asked about something not listed, say you don't have it here: it may be in
  another zone or may have been forgotten. Never guess what hidden memories contain.
- Text like [private detail] was removed for privacy; work around it politely.
- Don't talk about what you saved or forgot; the app shows that separately.
- Keep replies short (under 150 words) unless the user asks for more.
Call the reply tool with your answer and the ids of memories you actually used."""

FACT_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "short": {"type": "string"},
        "category": {"type": "string", "enum": CATEGORY_VALUES},
        "sensitivity": {"type": "string", "enum": ["low", "medium", "high"]},
        "confidence": {"type": "number"},
        "is_about_user": {"type": "boolean"},
        "is_temporary": {"type": "boolean"},
        "expires_in_hours": {"type": ["integer", "null"]},
        "suggested_zone": {"type": "string", "enum": ZONE_VALUES},
    },
    "required": ["content", "short", "category", "sensitivity", "confidence"],
}


def _coerce_fact(raw):
    """Validate one fact from the model; repair small problems instead of failing."""
    if not isinstance(raw, dict) or not str(raw.get("content", "")).strip():
        return None
    data = dict(raw)
    data["content"] = str(data["content"]).strip()[:500]
    data["short"] = (str(data.get("short") or "").strip() or data["content"][:40])[:60]
    if data.get("category") not in CATEGORY_VALUES:
        data["category"] = "other"
    if data.get("sensitivity") not in {"low", "medium", "high"}:
        data["sensitivity"] = "medium"
    if data.get("suggested_zone") not in ZONE_VALUES:
        data["suggested_zone"] = "global"
    try:
        data["confidence"] = min(1.0, max(0.0, float(data.get("confidence", 0.8))))
    except (TypeError, ValueError):
        data["confidence"] = 0.8
    if data.get("expires_in_hours") is not None:
        try:
            data["expires_in_hours"] = int(data["expires_in_hours"])
        except (TypeError, ValueError):
            data["expires_in_hours"] = None
    data.pop("sensitive_span", None)  # secrets are only detected locally
    try:
        return CandidateFact.model_validate(data)
    except Exception:  # noqa: BLE001
        logger.warning("Skipping invalid fact from model: %s", data)
        return None


class AnthropicLLM:
    def __init__(self, api_key, model):
        self.client = Anthropic(api_key=api_key, timeout=45, max_retries=2)
        self.model = model

    def _call_tool(self, system, messages, tool):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=messages,
        )
        block = next(block for block in response.content if block.type == "tool_use")
        return block.input

    def extract(self, message, zone, history):
        tool = {
            "name": "save_candidates",
            "description": "Return the user's lasting facts and any explicit memory command.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "command_target": {"type": ["string", "null"]},
                    "facts": {"type": "array", "items": FACT_SCHEMA},
                },
                "required": ["command", "facts"],
            },
        }
        messages = self._history_messages(history)
        messages.append({"role": "user", "content": message})
        try:
            data = self._call_tool(EXTRACT_SYSTEM.format(zone=zone), messages, tool)
        except Exception:
            logger.exception("Claude extraction failed; continuing with no extracted facts")
            return ExtractionResult()
        facts = [fact for fact in map(_coerce_fact, data.get("facts") or []) if fact]
        command = str(data.get("command") or "none")
        valid = {"none", "remember", "dont_remember", "forget", "use_once"}
        if command not in valid and not command.startswith("zone_only:"):
            command = "none"
        return ExtractionResult(
            command=command,
            command_target=data.get("command_target"),
            facts=facts,
        )

    def answer(self, message, zone, allowed, withheld_counts, history):
        tool = {
            "name": "reply",
            "description": "Give your answer and list the memory ids you actually used.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "used_memory_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["text", "used_memory_ids"],
            },
        }
        memory_lines = "\n".join(
            f"[m:{item['id']}] {item['content']}" for item in allowed
        ) or "(none)"
        hidden = ", ".join(f"{key}: {value}" for key, value in withheld_counts.items()) or "none"
        messages = self._history_messages(history)
        messages.append({"role": "user", "content": message})
        try:
            data = self._call_tool(
                ANSWER_SYSTEM.format(zone=zone, memories=memory_lines, hidden=hidden),
                messages,
                tool,
            )
            ids = []
            for value in data.get("used_memory_ids") or []:
                try:
                    ids.append(int(value))
                except (TypeError, ValueError):
                    continue
            return AnswerResult(text=str(data.get("text") or "").strip() or "…", used_memory_ids=ids)
        except Exception as error:
            logger.exception("Claude answer failed")
            detail = str(error)
            if "authentication" in detail.lower() or "401" in detail:
                text = "Claude rejected the API key. Check ANTHROPIC_API_KEY in your .env file and restart."
            elif "model" in detail.lower() and "not" in detail.lower():
                text = "Claude couldn't find the model in ANTHROPIC_MODEL. Check your .env file."
            else:
                text = "I couldn't reach Claude just now (check your internet connection). Your memories are unchanged."
            return AnswerResult(text=text, used_memory_ids=[])

    @staticmethod
    def _history_messages(history):
        """Claude needs alternating roles starting with the user."""
        messages = []
        for item in history[-10:]:
            role, content = item.get("role"), (item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"] += "\n" + content
            else:
                messages.append({"role": role, "content": content})
        while messages and messages[0]["role"] != "user":
            messages.pop(0)
        if messages and messages[-1]["role"] == "user":
            messages.pop()  # the new user message is appended by the caller
        return messages


def get_llm():
    if not settings.anthropic_api_key or settings.anthropic_api_key == "replace-with-your-own-key":
        raise RuntimeError(
            "Claude isn't set up yet. Add your API key to the .env file "
            "(ANTHROPIC_API_KEY=sk-ant-...) and restart the backend."
        )
    return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
