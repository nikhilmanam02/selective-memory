from app.memory_store import insert_memory

DEMO_MEMORIES = [
    {
        "content": "User is vegetarian",
        "short": "vegetarian",
        "category": "preference",
        "zone": "global",
        "rule": "forever",
        "sensitivity": "low",
    },
    {
        "content": "User's sister is Priya",
        "short": "sister’s name",
        "category": "relationship",
        "zone": "global",
        "rule": "forever",
        "sensitivity": "low",
    },
    {
        "content": "User works as a product designer at Northwind",
        "short": "work details",
        "category": "work",
        "zone": "work",
        "rule": "zone_only",
        "sensitivity": "medium",
    },
    {
        "content": "User has an anxiety-related doctor appointment on Friday",
        "short": "doctor appointment",
        "category": "health",
        "zone": "health",
        "rule": "zone_only",
        "sensitivity": "high",
    },
    {
        "content": "User is interviewing at other companies",
        "short": "job search",
        "category": "job_search",
        "zone": "personal",
        "rule": "zone_only",
        "sensitivity": "high",
    },
]


def seed_demo(connection):
    for memory in DEMO_MEMORIES:
        insert_memory(
            connection, **memory, reason="Seeded demo memory", source="Sample data"
        )
