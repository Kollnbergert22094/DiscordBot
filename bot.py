import discord
from discord import app_commands
import os
import json

TOKEN = os.getenv("DISCORD_TOKEN")

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

DATA_FILE = "pools.json"

def load_pools():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_pools(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

pools = load_pools()

@client.tree.command(name="create_pool", description="Erstellt einen neuen Pool")
@app_commands.describe(
    pool_name="Name des Pools", 
    items_string="Items durch Komma getrennt (z.B. Item1, Item2, Item3)"
)
async def create_pool(interaction: discord.Interaction, pool_name: str, items_string: str):
    item_list = [i.strip() for i in items_string.split(",")]
    
    if pool_name in pools:
        await interaction.response.send_message(f"Pool `{pool_name}` existiert bereits!", ephemeral=True)
        return

    pools[pool_name] = {"all": item_list, "hidden": []}
    save_pools(pools)
    
    await interaction.response.send_message(
        f"Pool `{pool_name}` erstellt mit {len(item_list)} Items."
    )

@client.tree.command(name="delete_pool", description="Einen pool löschen")
@app_commands.describe(
    pool_name="Name des Pools"
)
async def delete_pool(interaction: discord.Interaction, pool_name: str):

    if pool_name not in pools:
        await interaction.response.send_message(f"Pool `{pool_name}` existiert nicht!", ephemeral=True)
        return

    del pools[pool_name]

    save_pools(pools)

    await interaction.response.send_message(
        f"Pool `{pool_name}`erfolgreich gelöscht."
    )

@client.tree.command(name="show_pools", description="Alle Pools anzeigen")
async def show_pools(interaction: discord.Interaction):

    if not pools:
        await interaction.response.send_message("Es wurden noch keine Pools erstellt.", ephemeral=True)
        return

    pool_namen = ", ".join([f"`{name}`" for name in pools.keys()])

    await interaction.response.send_message(f"Verfügbare Pools: {pool_namen}")

client.run(TOKEN)