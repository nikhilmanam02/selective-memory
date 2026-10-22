import hashlib
import secrets

from app.memory_store import now_iso

APP_ZONES = ("personal", "work", "health", "finance")


def _clean_zones(zones):
    if isinstance(zones, str):
        zones = zones.split(",")
    picked = [zone for zone in APP_ZONES if zone in set(zones or [])]
    return picked


def _row_to_profile(row):
    data = dict(row)
    zones = [z for z in (data.get("zones") or data.get("zone") or "").split(",") if z]
    data["zones"] = zones
    data["zone"] = zones[0] if zones else "personal"
    data["can_write"] = bool(data.get("can_write", 1))
    data.pop("token_hash", None)
    return data


def create_connection(connection, name, zones, can_write=True):
    zones = _clean_zones(zones)
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cursor = connection.execute(
        """
        INSERT INTO connections(name, zone, zones, can_write, token_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            name.strip(),
            zones[0] if zones else "personal",
            ",".join(zones),
            1 if can_write else 0,
            digest,
            now_iso(),
        ),
    )
    profile = get_connection(connection, cursor.lastrowid)
    return {**profile, "token": token}


def get_connection(connection, connection_id):
    row = connection.execute(
        "SELECT id, name, zone, zones, can_write, created_at, last_used_at "
        "FROM connections WHERE id = ?",
        (connection_id,),
    ).fetchone()
    return _row_to_profile(row) if row else None


def list_connections(connection):
    rows = connection.execute(
        "SELECT id, name, zone, zones, can_write, created_at, last_used_at "
        "FROM connections ORDER BY id DESC"
    )
    return [_row_to_profile(row) for row in rows]


def update_connection(connection, connection_id, zones=None, can_write=None):
    if zones is not None:
        cleaned = _clean_zones(zones)
        connection.execute(
            "UPDATE connections SET zones = ?, zone = ? WHERE id = ?",
            (",".join(cleaned), cleaned[0] if cleaned else "personal", connection_id),
        )
    if can_write is not None:
        connection.execute(
            "UPDATE connections SET can_write = ? WHERE id = ?",
            (1 if can_write else 0, connection_id),
        )
    return get_connection(connection, connection_id)


def revoke_connection(connection, connection_id):
    cursor = connection.execute("DELETE FROM connections WHERE id = ?", (connection_id,))
    return cursor.rowcount > 0


def authenticate(connection, token):
    if not token:
        return None
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = connection.execute(
        "SELECT id FROM connections WHERE token_hash = ?", (digest,)
    ).fetchone()
    if not row:
        return None
    connection.execute(
        "UPDATE connections SET last_used_at = ? WHERE id = ?", (now_iso(), row["id"])
    )
    return get_connection(connection, row["id"])
