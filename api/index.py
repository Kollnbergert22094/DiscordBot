from fastapi import FastAPI, Request, HTTPException
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from upstash_redis import Redis
import os, json, random

app = FastAPI()
verify_key = VerifyKey(bytes.fromhex(os.environ["DISCORD_PUBLIC_KEY"]))
redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ["KV_REST_API_URL"],
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ["KV_REST_API_TOKEN"],
)
POOLS = "pools"  # Redis-Hash: pool_name -> JSON {"all": [...], "hidden": [...]}
# "all"    = alle Items im Pool
# "hidden" = bereits gezogene Items (werden bei /draw übersprungen, bis /reset_pool)

EPHEMERAL = 64
rng = random.SystemRandom()


# ---------- Hilfsfunktionen ----------

def reply(text: str, ephemeral: bool = False):
    if len(text) > 2000:  # Discord-Limit pro Nachricht
        text = text[:1990] + "\n…"
    data = {"content": text}
    if ephemeral:
        data["flags"] = EPHEMERAL
    return {"type": 4, "data": data}


def get_options(data) -> dict:
    return {o["name"]: o["value"] for o in data["data"].get("options", [])}


def split_items(s: str) -> list[str]:
    return [i.strip() for i in s.split(",") if i.strip()]


def load_pool(name: str):
    raw = redis.hget(POOLS, name)
    return json.loads(raw) if raw is not None else None


def save_pool(name: str, pool: dict):
    redis.hset(POOLS, name, json.dumps(pool))


def not_found(name: str):
    return reply(f"Pool `{name}` existiert nicht!", ephemeral=True)


# ---------- Pools ----------

def create_pool(opts):
    name = opts["pool_name"].strip()
    items = split_items(opts["items_string"])

    if redis.hexists(POOLS, name):
        return reply(f"Pool `{name}` existiert bereits!", ephemeral=True)

    save_pool(name, {"all": items, "hidden": []})
    return reply(f"Pool `{name}` erstellt mit {len(items)} Items.", ephemeral=True)


def delete_pool(opts):
    name = opts["pool_name"].strip()
    if not redis.hexists(POOLS, name):
        return not_found(name)

    redis.hdel(POOLS, name)
    return reply(f"Pool `{name}` erfolgreich gelöscht.")


def show_pools(opts):
    names = redis.hkeys(POOLS)
    if not names:
        return reply("Es wurden noch keine Pools erstellt.", ephemeral=True)
    return reply("Verfügbare Pools: " + ", ".join(f"`{n}`" for n in sorted(names, key=str.casefold)))


def show_items(opts):
    name = opts["pool_name"].strip()
    pool = load_pool(name)
    if pool is None:
        return not_found(name)

    items = sorted(pool["all"], key=str.casefold)
    if not items:
        return reply(f"Pool `{name}` ist leer.", ephemeral=True)

    hidden = set(pool["hidden"])
    lines = [f"• ~~{i}~~" if i in hidden else f"• {i}" for i in items]
    header = f"**{name}** ({len(items)} Items, {len(items) - len(hidden)} noch ziehbar):"
    return reply(header + "\n" + "\n".join(lines))


# ---------- Items hinzufügen / entfernen ----------

def add_items(opts):
    name = opts["pool_name"].strip()
    pool = load_pool(name)
    if pool is None:
        return not_found(name)

    existing = {i.casefold() for i in pool["all"]}
    added, skipped = [], []
    for item in split_items(opts["items"]):
        if item.casefold() in existing:
            skipped.append(item)
        else:
            pool["all"].append(item)
            existing.add(item.casefold())
            added.append(item)

    save_pool(name, pool)

    msg = f"{len(added)} Item(s) zu `{name}` hinzugefügt"
    msg += ": " + ", ".join(added) if added else "."
    if skipped:
        msg += f"\nSchon vorhanden: {', '.join(skipped)}"
    return reply(msg, ephemeral=True)


def remove_items(opts):
    name = opts["pool_name"].strip()
    pool = load_pool(name)
    if pool is None:
        return not_found(name)

    to_remove = {i.casefold() for i in split_items(opts["items"])}
    removed = [i for i in pool["all"] if i.casefold() in to_remove]
    pool["all"] = [i for i in pool["all"] if i.casefold() not in to_remove]
    pool["hidden"] = [i for i in pool["hidden"] if i.casefold() not in to_remove]

    found = {i.casefold() for i in removed}
    missing = [i for i in split_items(opts["items"]) if i.casefold() not in found]

    save_pool(name, pool)

    msg = f"{len(removed)} Item(s) aus `{name}` entfernt"
    msg += ": " + ", ".join(removed) if removed else "."
    if missing:
        msg += f"\nNicht gefunden: {', '.join(missing)}"
    return reply(msg, ephemeral=True)


# ---------- Auslosung ----------

def draw(opts):
    name = opts["pool_name"].strip()
    count = opts.get("anzahl", 1)
    put_back = opts.get("zuruecklegen", False)

    pool = load_pool(name)
    if pool is None:
        return not_found(name)

    hidden = set(pool["hidden"])
    available = pool["all"] if put_back else [i for i in pool["all"] if i not in hidden]

    if not available:
        return reply(f"In `{name}` sind keine Items mehr übrig. Mit `/reset_pool` neu starten.", ephemeral=True)
    if count > len(available):
        return reply(f"Es sind nur noch {len(available)} Item(s) in `{name}` übrig.", ephemeral=True)

    drawn = rng.sample(available, count)

    if not put_back:
        pool["hidden"].extend(drawn)
        save_pool(name, pool)

    if count == 1:
        msg = f"🎲 Gezogen aus `{name}`: **{drawn[0]}**"
    else:
        msg = f"🎲 Gezogen aus `{name}`:\n" + "\n".join(f"{n}. **{i}**" for n, i in enumerate(drawn, 1))

    if not put_back:
        msg += f"\n-# Noch {len(available) - count} Item(s) übrig"
    return reply(msg)


def reset_pool(opts):
    name = opts["pool_name"].strip()
    pool = load_pool(name)
    if pool is None:
        return not_found(name)

    pool["hidden"] = []
    save_pool(name, pool)
    return reply(f"Pool `{name}` zurückgesetzt, alle {len(pool['all'])} Item(s) sind wieder ziehbar.")


# ---------- Autovervollständigung ----------

def matches(candidates, typed: str):
    t = typed.casefold()
    hits = [c for c in candidates if t in c.casefold()]
    # Treffer am Anfang zuerst, dann alphabetisch
    return sorted(hits, key=lambda c: (not c.casefold().startswith(t), c.casefold()))


def autocomplete(data):
    cmd = data["data"]["name"]
    opts = data["data"].get("options", [])
    focused = next((o for o in opts if o.get("focused")), None)
    choices = []

    if focused and focused["name"] == "pool_name":
        names = redis.hkeys(POOLS) or []
        choices = [{"name": n[:100], "value": n} for n in matches(names, str(focused["value"]))]

    elif focused and focused["name"] == "items" and cmd == "remove_items":
        pool_name = next((str(o["value"]).strip() for o in opts if o["name"] == "pool_name"), "")
        pool = load_pool(pool_name)
        if pool:
            # Bei "Apfel, Ban" nur das letzte Stück vervollständigen
            parts = [p.strip() for p in str(focused["value"]).split(",")]
            done, current = [p for p in parts[:-1] if p], parts[-1]
            chosen = {p.casefold() for p in done}
            for item in matches([i for i in pool["all"] if i.casefold() not in chosen], current):
                value = ", ".join(done + [item])  # landet im Eingabefeld
                if len(value) <= 100:
                    # angezeigt wird nur das neue Item, nicht die ganze Liste
                    choices.append({"name": item[:100], "value": value})

    return {"type": 8, "data": {"choices": choices[:25]}}


COMMANDS = {
    "create_pool": create_pool,
    "delete_pool": delete_pool,
    "show_pools": show_pools,
    "show_items": show_items,
    "add_items": add_items,
    "remove_items": remove_items,
    "draw": draw,
    "reset_pool": reset_pool,
}


# ---------- Endpoint ----------

@app.post("/api/interactions")
@app.post("/interactions")
@app.post("/")
async def interactions(request: Request):
    sig = request.headers.get("X-Signature-Ed25519", "")
    ts = request.headers.get("X-Signature-Timestamp", "")
    body = await request.body()
    try:
        verify_key.verify(ts.encode() + body, bytes.fromhex(sig))
    except (BadSignatureError, ValueError):
        raise HTTPException(401, "invalid request signature")

    data = json.loads(body)

    if data["type"] == 1:  # PING
        return {"type": 1}

    if data["type"] == 2:  # Slash-Command
        handler = COMMANDS.get(data["data"]["name"])
        if handler:
            return handler(get_options(data))

    if data["type"] == 4:  # Autocomplete beim Tippen
        return autocomplete(data)

    return reply("Unbekannter Command", ephemeral=True)