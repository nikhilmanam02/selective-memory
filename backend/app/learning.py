from datetime import datetime, timezone

from app.config import settings

LEARNABLE_BEHAVIORS = {
    "forever": "auto_forever",
    "zone_only": "zone_only",
    "session": "session",
    "decline": "never",
}


def get_preferences(connection):
    return {
        row["category"]: {
            "behavior": row["behavior"],
            "zone": row["zone"],
            "source": row["source"],
        }
        for row in connection.execute("SELECT * FROM learned_prefs")
    }


def get_all_preferences(connection, categories):
    current = get_preferences(connection)
    defaults = {
        "preference": ("auto_forever", "global"),
        "identity": ("auto_forever", "global"),
        "relationship": ("auto_forever", "global"),
        "schedule": ("auto_forever", "global"),
        "location": ("auto_forever", "global"),
        "work": ("zone_only", "work"),
        "health": ("ask", "health"),
        "finance": ("ask", "finance"),
        "secret": ("use_once", None),
        "job_search": ("ask", "personal"),
        "other": ("ask", None),
    }
    return [
        {
            "category": category,
            **current.get(
                category,
                {
                    "behavior": defaults.get(category, ("ask", None))[0],
                    "zone": defaults.get(category, ("ask", None))[1],
                    "source": "default",
                },
            ),
        }
        for category in categories
    ]


def record_choice(connection, category, choice, zone=None):
    if category == "secret":
        return None
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "INSERT INTO ask_answers(category, choice, zone, created_at) VALUES (?, ?, ?, ?)",
        (category, choice, zone, now),
    )
    threshold = 2 if choice == "undo" else settings.learn_threshold
    rows = connection.execute(
        "SELECT choice, zone FROM ask_answers WHERE category = ? ORDER BY id DESC LIMIT ?",
        (category, threshold),
    ).fetchall()
    if len(rows) < threshold:
        return None
    latest = [(row["choice"], row["zone"]) for row in rows]
    if selected_undo := (latest[0][0] == "undo"):
        if any(choice != "undo" for choice, _ in latest):
            return None
    elif latest[0][0] == "decline":
        if any(choice != "decline" for choice, _ in latest):
            return None
    elif any(item != latest[0] for item in latest):
        return None

    selected = latest[0][0]
    if selected_undo:
        behavior, learned_zone = "ask", zone
    else:
        behavior = LEARNABLE_BEHAVIORS.get(selected)
        learned_zone = zone if selected == "zone_only" else None
    if not behavior:
        return None
    connection.execute(
        """
        INSERT INTO learned_prefs(category, behavior, zone, source, updated_at)
        VALUES (?, ?, ?, 'learned', ?)
        ON CONFLICT(category) DO UPDATE SET
          behavior=excluded.behavior, zone=excluded.zone,
          source='learned', updated_at=excluded.updated_at
        """,
        (category, behavior, learned_zone, now),
    )
    if behavior == "never":
        message = f"Got it. I won't save {category.replace('_', ' ')} information unless you explicitly ask."
    elif behavior == "ask":
        message = f"I'll check with you before saving {category.replace('_', ' ')} information."
    else:
        destination = f"your {learned_zone.title()} zone" if learned_zone else "all zones"
        message = f"Got it. I'll keep {category.replace('_', ' ')} info in {destination} from now on without asking."
    return {
        "category": category,
        "behavior": behavior,
        "zone": learned_zone,
        "message": message,
    }


def set_manual_preference(connection, category, behavior, zone=None):
    if category == "secret":
        behavior, zone = "use_once", None
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO learned_prefs(category, behavior, zone, source, updated_at)
        VALUES (?, ?, ?, 'manual', ?)
        ON CONFLICT(category) DO UPDATE SET
          behavior=excluded.behavior, zone=excluded.zone,
          source='manual', updated_at=excluded.updated_at
        """,
        (category, behavior, zone, now),
    )
