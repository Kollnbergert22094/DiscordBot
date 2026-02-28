import discord
from discord import app_commands

TOKEN = ''

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Dies verbindet deine Befehle mit Discord
        await self.tree.sync()

client = MyClient()

@client.tree.command(name="ping", description="Testet die Antwortzeit")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🏓")

client.run(TOKEN)