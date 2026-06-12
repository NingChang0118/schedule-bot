import discord
from discord import app_commands
from discord.ext import commands


class TestCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="測試",
        description="測試排班機器人是否正常運作"
    )
    async def test(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_message(
            "排班機器人正常運作 ✅",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(TestCog(bot))