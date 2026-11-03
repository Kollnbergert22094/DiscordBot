from fastapi import FastAPI, Request, HTTPException
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from upstash_redis import Redis
import os, json

app = FastAPI()
verify_key = VerifyKey(bytes.fromhex(os.environ["DISCORD_PUBLIC_KEY"]))
redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ["KV_REST_API_URL"],
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ["KV_REST_API_TOKEN"],
)
POOLS = "pools"  # Redis-Hash: pool_name -> JSON {"all": [...], "hidden": [...]}

EPHEMERAL = 64


def reply(text: str, ephemeral: bool = False):
    data = {"content": text}
    if ephemeral:
        data["flags"] = EPHEMERAL
    return {"type": 4, "data": data}


def get_options(data) -> dict:
    return {o["name"]: o["value"] for o in data["data"].get("options", [])}


# ---------- Commands ----------

def create_pool(opts):
    name = opts["pool_name"].strip()
    items = [i.strip() for i in opts["items_string"].split(",") if i.strip()]

    if redis.hexists(POOLS, name):
        return reply(f"Pool `{name}` existiert bereits!", ephemeral=True)

    redis.hset(POOLS, name, json.dumps({"all": items, "hidden": []}))
    return reply(f"Pool `{name}` erstellt mit {len(items)} Items.", ephemeral=True)


def delete_pool(opts):
    name = opts["pool_name"].strip()
    if not redis.hexists(POOLS, name):
        return reply(f"Pool `{name}` existiert nicht!", ephemeral=True)

    redis.hdel(POOLS, name)
    return reply(f"Pool `{name}` erfolgreich gelöscht.")


def show_pools(opts):
    names = redis.hkeys(POOLS)
    if not names:
        return reply("Es wurden noch keine Pools erstellt.", ephemeral=True)
    return reply("Verfügbare Pools: " + ", ".join(f"`{n}`" for n in sorted(names)))


COMMANDS = {
    "create_pool": create_pool,
    "delete_pool": delete_pool,
    "show_pools": show_pools,
}


# ---------- Endpoint ----------

@app.post("/api/interactions")
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

    return reply("Unbekannter Command", ephemeral=True)