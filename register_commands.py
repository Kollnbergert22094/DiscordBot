# Lokal ausführen, jedes Mal wenn sich Commands ändern:
#   pip install requests python-dotenv
#   python register_commands.py
# Braucht eine .env im selben Ordner mit DISCORD_APP_ID und DISCORD_TOKEN.
import requests, os
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.environ["DISCORD_APP_ID"]
TOKEN = os.environ["DISCORD_TOKEN"]

STRING, INTEGER, BOOLEAN = 3, 4, 5

POOL_NAME = {"type": STRING, "name": "pool_name", "description": "Name des Pools", "required": True}
# Gleiche Option, aber Discord schlägt beim Tippen vorhandene Pools vor
POOL_SELECT = {**POOL_NAME, "autocomplete": True}

commands = [
    {
        "name": "create_pool",
        "description": "Erstellt einen neuen Pool",
        "options": [
            POOL_NAME,
            {"type": STRING, "name": "items_string",
             "description": "Items durch Komma getrennt (z.B. Item1, Item2, Item3)", "required": True},
        ],
    },
    {"name": "delete_pool", "description": "Einen Pool löschen", "options": [POOL_SELECT]},
    {"name": "show_pools", "description": "Alle Pools anzeigen"},
    {"name": "show_items", "description": "Alle Items eines Pools alphabetisch anzeigen", "options": [POOL_SELECT]},
    {
        "name": "add_items",
        "description": "Items zu einem Pool hinzufügen",
        "options": [
            POOL_SELECT,
            {"type": STRING, "name": "items", "description": "Ein Item oder mehrere durch Komma getrennt", "required": True},
        ],
    },
    {
        "name": "remove_items",
        "description": "Items aus einem Pool entfernen",
        "options": [
            POOL_SELECT,
            {"type": STRING, "name": "items", "description": "Ein Item oder mehrere durch Komma getrennt",
             "required": True, "autocomplete": True},
        ],
    },
    {
        "name": "draw",
        "description": "Zufällig Items aus einem Pool ziehen",
        "options": [
            POOL_SELECT,
            {"type": INTEGER, "name": "anzahl", "description": "Wie viele Items (Standard: 1)",
             "required": False, "min_value": 1, "max_value": 100},
            {"type": BOOLEAN, "name": "zuruecklegen",
             "description": "Gezogene Items im Pool lassen (Standard: nein)", "required": False},
        ],
    },
    {"name": "reset_pool", "description": "Alle gezogenen Items wieder ziehbar machen", "options": [POOL_SELECT]},
]

r = requests.put(
    f"https://discord.com/api/v10/applications/{APP_ID}/commands",
    headers={"Authorization": f"Bot {TOKEN}"},
    json=commands,
)
print(r.status_code, r.json() if r.ok else r.text)