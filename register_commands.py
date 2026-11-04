# Einmal lokal ausführen (und jedes Mal, wenn sich Commands ändern):
#   pip install requests
#   DISCORD_APP_ID=... DISCORD_TOKEN=... python register_commands.py
import requests, os

APP_ID = os.environ["DISCORD_APP_ID"]
TOKEN = os.environ["DISCORD_TOKEN"]
STRING = 3

commands = [
    {
        "name": "create_pool",
        "description": "Erstellt einen neuen Pool",
        "options": [
            {"type": STRING, "name": "pool_name", "description": "Name des Pools", "required": True},
            {"type": STRING, "name": "items_string",
             "description": "Items durch Komma getrennt (z.B. Item1, Item2, Item3)", "required": True},
        ],
    },
    {
        "name": "delete_pool",
        "description": "Einen Pool löschen",
        "options": [
            {"type": STRING, "name": "pool_name", "description": "Name des Pools", "required": True},
        ],
    },
    {"name": "show_pools", "description": "Alle Pools anzeigen"},
    {
        "name": "show_items",
        "description": "Alle Items eines Pools alphabetisch anzeigen",
        "options": [
            {"type": STRING, "name": "pool_name", "description": "Name des Pools", "required": True},
        ],
    },
]

r = requests.put(
    f"https://discord.com/api/v10/applications/{APP_ID}/commands",
    headers={"Authorization": f"Bot {TOKEN}"},
    json=commands,
)
print(r.status_code, r.json())