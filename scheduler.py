import asyncio
import datetime
import pytz
import discord

from discord.ui import View, Button
from database import get_boss_notifications, get_notification_settings, remove_boss_notification
from enumOptions import OWNER_ICONS

local_tz = pytz.timezone("Asia/Bangkok")  # ตั้งเวลาเป็นไทย

async def schedule_boss_notifications(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.datetime.now(local_tz)

        for guild in bot.guilds:
            guild_id = str(guild.id)
            notifications = get_boss_notifications(guild_id)
            settings = get_notification_settings(guild_id)

            if not notifications or not settings["room"]:
                continue

            room = bot.get_channel(settings["room"])
            role_mention = f"<@&{settings['role']}>" if settings["role"] else ""

            for boss in notifications:
                spawn_time = now.replace(hour=boss["hours"], minute=boss["minutes"], second=0)
                time_until_spawn = (spawn_time - now).total_seconds()
                time_before_five_min = max(time_until_spawn - 300, 0)

                if time_until_spawn > 0:
                    await asyncio.sleep(time_before_five_min)
                    embed = discord.Embed(
                        title="𝐁𝐨𝐬𝐬 𝐍𝐨𝐭𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧!!",
                        description=f"{OWNER_ICONS.get(boss['owner'], '❓')} 𝐁𝐨𝐬𝐬 {boss['boss_name']} 𝐢𝐬 𝐬𝐩𝐚𝐰𝐧𝐢𝐧𝐠 𝐢𝐧 𝟓 𝐦𝐢𝐧𝐮𝐭𝐞𝐬! {role_mention}",
                        color=discord.Color.yellow()
                    )
                    await room.send(embed=embed)
                    await asyncio.sleep(300)

                    embed = discord.Embed(
                        title="𝐁𝐨𝐬𝐬 𝐡𝐚𝐬 𝐬𝐩𝐚𝐰𝐧!!",
                        description=f"{OWNER_ICONS.get(boss['owner'], '❓')} 𝐁𝐨𝐬𝐬 {boss['boss_name']} 𝐡𝐚𝐬 𝐒𝐩𝐚𝐰𝐧 𝐋𝐞𝐭'𝐬 𝐟𝐢𝐠𝐡𝐭! {role_mention}",
                        color=discord.Color.red()
                    )
                    await room.send(embed=embed)
                    remove_boss_notification(guild_id, boss["boss_name"])
                    await asyncio.sleep(2)

        await asyncio.sleep(60)  # ตรวจสอบทุกๆ 1 นาที

class ConfirmView(discord.ui.View):
    def __init__(self, embed, guild_id):
        super().__init__(timeout=60)
        self.embed = embed
        self.guild_id = guild_id

    @discord.ui.button(label="📢 ประกาศ", style=discord.ButtonStyle.green)
    async def announce(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.defer()

        settings = get_notification_settings(self.guild_id)
        if not settings["room"]:
            return await interaction.followup.send("❌ ยังไม่ได้ตั้งค่าห้องแจ้งเตือนบอส!", ephemeral=True)

        channel = interaction.guild.get_channel(settings["room"])
        if not channel:
            return await interaction.followup.send("❌ ไม่พบช่องแจ้งเตือน!", ephemeral=True)

        role_mention = f"<@&{settings['role']}>" if settings["role"] else "@everyone"

        await channel.send(f"📢 **【𝐓𝐢𝐦𝐞 𝐢𝐧 𝐠𝐚𝐦𝐞 + 𝟏𝐡𝐫】** {role_mention}", embed=self.embed)
        await interaction.followup.send("✅ ประกาศไปที่ห้องแจ้งเตือนเรียบร้อย!", ephemeral=True)
