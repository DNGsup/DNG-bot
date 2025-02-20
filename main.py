import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from datetime import datetime, timedelta
import random

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

giveaways = {}
giveaway_room = {}

class GiveawayModal(discord.ui.Modal, title="สร้างกิจกรรมสุ่มรางวัล"):
    prize = discord.ui.TextInput(label="ชื่อรางวัล", placeholder="ใส่ชื่อรางวัล", required=True)
    amount = discord.ui.TextInput(label="จำนวนรางวัล", placeholder="ใส่จำนวนรางวัล", required=True)
    winners = discord.ui.TextInput(label="จำนวนผู้ชนะ", placeholder="ใส่จำนวนผู้ชนะ", required=True)
    duration = discord.ui.TextInput(label="ระยะเวลา (s/m/h/d)", placeholder="เช่น 30s, 5m, 2h", required=True)

    def __init__(self, interaction: discord.Interaction, role: discord.Role, image_url: str):
        super().__init__()
        self.interaction = interaction
        self.role = role
        self.image_url = image_url

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            winners = int(self.winners.value)
            duration_seconds = parse_duration(self.duration.value)

            if duration_seconds is None or duration_seconds < 30 or duration_seconds > 604800:
                await interaction.response.send_message("ระยะเวลาต้องอยู่ระหว่าง 30 วินาทีถึง 7 วัน (7d)", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("จำนวนรางวัลและจำนวนผู้ชนะต้องเป็นตัวเลข", ephemeral=True)
            return

        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)

        embed = discord.Embed(
            title=f"🎁 {self.prize.value} ({amount} รางวัล)",
            color=discord.Color.gold()
        )
        embed.add_field(name="🏆 จำนวนผู้ชนะ", value=str(winners), inline=True)
        embed.add_field(name="🛡️ โรลที่เข้าร่วมได้", value=self.role.mention, inline=True)
        embed.add_field(name="⏳ สิ้นสุดใน", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
        embed.add_field(name="👥 จำนวนคนเข้าร่วม", value="0", inline=False)

        if self.image_url:
            embed.set_image(url=self.image_url)

        guild_id = str(interaction.guild_id)
        target_channel = bot.get_channel(giveaway_room.get(guild_id, interaction.channel.id))

        view = JoinButton(interaction.channel.id, self.role.id)
        message = await target_channel.send(content="🎉 **กิจกรรมสุ่มรางวัลเริ่มแล้ว!!**", embed=embed, view=view)

        giveaways[interaction.channel.id] = {
            "prize": self.prize.value,
            "amount": amount,
            "winners": winners,
            "entries": [],
            "end_time": end_time,
            "embed": embed,
            "embed_message": message,
            "view": view,
            "role_id": self.role.id,
            "image_url": self.image_url
        }

        await interaction.response.send_message("✅ กิจกรรมเริ่มต้นแล้ว!", ephemeral=True)
        await asyncio.sleep(duration_seconds)
        await end_giveaway(interaction.channel.id)

class JoinButton(discord.ui.View):
    def __init__(self, giveaway_id, role_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.role_id = role_id

    @discord.ui.button(label="เข้าร่วม", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = giveaways.get(self.giveaway_id)
        if not giveaway:
            await interaction.response.send_message("❌ กิจกรรมนี้สิ้นสุดลงแล้ว", ephemeral=True)
            return

        if not any(role.id == self.role_id for role in interaction.user.roles):
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์เข้าร่วมกิจกรรมนี้", ephemeral=True)
            return

        if interaction.user.id in giveaway["entries"]:
            await interaction.response.send_message("⚠️ คุณเข้าร่วมกิจกรรมนี้ไปแล้ว!", ephemeral=True)
            return

        giveaway["entries"].append(interaction.user.id)
        giveaway["embed"].set_field_at(3, name="👥 จำนวนคนเข้าร่วม", value=str(len(giveaway["entries"])), inline=False)
        await giveaway["embed_message"].edit(embed=giveaway["embed"], view=self)

        await interaction.response.send_message("✅ คุณเข้าร่วมกิจกรรมแล้ว!", ephemeral=True)

@bot.tree.command(name="gcreate", description="สร้างกิจกรรมสุ่มรางวัล")
@app_commands.describe(role="เลือกโรลที่สามารถเข้าร่วมได้", image_url="ใส่ URL รูปภาพสำหรับกิจกรรม")
async def gcreate(interaction: discord.Interaction, role: discord.Role, image_url: str = None):
    if not image_url and interaction.message.attachments:
        image_url = interaction.message.attachments[0].url
    await interaction.response.send_modal(GiveawayModal(interaction, role, image_url or ""))

def parse_duration(duration: str):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        return int(duration[:-1]) * units[duration[-1]]
    except:
        return None

async def end_giveaway(channel_id):
    giveaway = giveaways.get(channel_id)
    if not giveaway:
        return

    giveaway["embed"].set_field_at(2, name="⏳ สิ้นสุดใน", value="`หมดเวลา`", inline=False)
    await giveaway["embed_message"].edit(embed=giveaway["embed"], view=None)

    target_channel = bot.get_channel(giveaway["embed_message"].channel.id)

    if not giveaway["entries"]:
        await target_channel.send("❌ ไม่มีผู้เข้าร่วมเพียงพอสำหรับการจับรางวัล")
        return

    winners = random.sample(giveaway["entries"], min(giveaway["winners"], len(giveaway["entries"])))

    for winner_id in winners:
        await target_channel.send(f"🎉 ยินดีด้วย! <@{winner_id}> ได้รับ {giveaway['prize']}!")

    giveaways.pop(channel_id, None)

bot.run(os.getenv('TOKEN'))
