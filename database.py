import json
import os
import re  # ✅ ใช้ Regular Expression
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# กำหนดตัวแปรฐานข้อมูลให้เป็น dictionary ว่างก่อน
broadcast_channels = {} # 1.เก็บห้อง broadcast เก็บในชีท
notification_room = {} # 2.เก็บห้องแจ้งเตือนบอส เก็บในชีท
notification_role = {} # 3.เก็บโรลแจ้งเตือนบอส เก็บในชีท
boss_notifications = {}  # 4.เพิ่มตัวแปรสำหรับจัดการแจ้งเตือนบอส
bp_summary_room = {} # 5.สำหรับเก็บห้องสรุปคะแนน เก็บในชีท
bp_reactions = {} # 6.สำหรับเก็บคะแนน เก็บในชีท
bp_data = {} # 7.สำหรับเก็บคะแนน
giveaway_room = {}  # 8.ห้องสำหรับจัดกิจกรรม เก็บในชีท
giveaways = {}       # 9.ข้อมูลของกิจกรรม
winner_history = {} # 10.เก็บจำนวนครั้งที่ผู้ใช้เคยชนะ (ในหน่วยความจำ) เก็บในชีท
# ------------------ extract_number_from_nickname ✅------------------
def extract_number_from_nickname(nickname):
    """ดึงเฉพาะตัวเลข 5 หลักแรกจาก Nickname"""
    match = re.search(r'\d{5}', nickname)  # ✅ ค้นหาเลข 5 หลักแรกที่พบ
    return match.group(0) if match else nickname  # ✅ ถ้ามีเลข 5 หลัก ให้ใช้เลขนั้น ถ้าไม่มีให้ใช้ชื่อเดิม
# ------------------ ตั้งค่า Google Sheets API ✅------------------
def init_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_json = os.getenv("GCP_CREDENTIALS")# โหลด Credentials จาก Render Environment Variables

    if not credentials_json:
        raise ValueError("❌ ไม่พบ GCP_CREDENTIALS ใน Environment Variables")

    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(credentials_json), scope)
    client = gspread.authorize(creds)
    return client
# ------------------ ตั้งค่า Google Sheets ------------------
client = init_sheets()
spreadsheet = client.open("Data form DC")
settings_sheet = spreadsheet.worksheet("Settings")
bosspoints_sheet = spreadsheet.worksheet("BossPoints")
# ------------------
def find_empty_row(sheet):
    """ ค้นหาแถวแรกที่ว่างใน Google Sheets """
    col_values = sheet.col_values(1)  # ดึงค่าทั้งคอลัมน์ A
    return len(col_values) + 1  # หาตำแหน่งแถวว่างแถวถัดไป
# ------------------
def update_bp_to_sheets(data, thread_name, guild):
    """อัปเดตคะแนน BP ไปยัง Google Sheets โดยระบุชื่อเธรด"""

    # ไม่ต้องอัปเดตหัวตารางซ้ำทุกครั้ง
    if bosspoints_sheet.cell(1, 1).value is None:
        bosspoints_sheet.update("A1", [["User ID", "No.", "name", "BP", "Thread name"]])

    start_row = find_empty_row(bosspoints_sheet)  # ✅ หาแถวว่าง
    rows = []
    for user_id, (username, bp) in data.items():
        member = guild.get_member(int(user_id))
        display_name = extract_number_from_nickname(member.display_name) if member else username
        rows.append([str(user_id), f"'{display_name}", None, bp, thread_name])  # ✅ เว้นช่อง C ไว้ให้สูตร / ใส่เครื่องหมาย ' ข้างหน้าตัวเลข

    cell_range = f"A{start_row}:E{start_row + len(rows) - 1}"
    bosspoints_sheet.update(cell_range, rows, value_input_option="RAW")  # ✅ เขียนลงแถวว่าง
# ------------------ ฟังก์ชันช่วยเหลือ ------------------
def find_row_by_key_and_guild(key: str, guild_id: str):
    """ค้นหาแถวในชีทตาม Key และ Guild ID"""
    keys = settings_sheet.col_values(1)  # คอลัมน์ Key
    guild_ids = settings_sheet.col_values(2)  # คอลัมน์ Guild ID

    for idx, (k, gid) in enumerate(zip(keys, guild_ids), start=1):
        if k == key and gid == guild_id:
            return idx
    return None

def save_to_sheet(key: str, guild_id: str, data):
    """บันทึกหรืออัปเดตข้อมูลลงในชีท"""
    row = find_row_by_key_and_guild(key, guild_id)
    json_data = json.dumps(data)  # แปลงข้อมูลเป็น JSON

    if row:
        # ✅ อัปเดตข้อมูลถ้ามีอยู่แล้ว
        settings_sheet.update_cell(row, 3, json_data)
    else:
        # ✅ เพิ่มแถวใหม่ถ้าไม่มีข้อมูลเดิม
        settings_sheet.append_row([key, guild_id, json_data])
# ---------------------------- load_settings ----------------------------
def load_settings():
    """โหลดการตั้งค่าทั้งหมดจากชีทมาเก็บในตัวแปร"""
    global broadcast_channels, notification_room, notification_role
    global bp_summary_room, bp_reactions, giveaway_room, winner_history

    rows = settings_sheet.get_all_records()
    for row in rows:
        key, guild_id, data_str = row['Key'], row['Guild ID'], row['Data']
        data = json.loads(data_str) if data_str else None

        if key == "broadcast_channels":
            broadcast_channels[guild_id] = set(data) if data else set()
        elif key == "notification_room":
            notification_room[guild_id] = data
        elif key == "notification_role":
            notification_role[guild_id] = data
        elif key == "bp_summary_room":
            bp_summary_room[guild_id] = data
        elif key == "bp_reactions":
            bp_reactions[guild_id] = data
        elif key == "giveaway_room":
            giveaway_room[guild_id] = data
        elif key == "winner_history":
            winner_history[guild_id] = data
# ---------------------------- save_settings ----------------------------
def save_settings():
    """บันทึกการตั้งค่าลง Google Sheets ในหน้า 'Settings'"""
    settings_data = []

    def add_setting(key, guild_id, data):
        settings_data.append([key, guild_id, str(data)])

    # บันทึก broadcast_channels
    for guild_id, channels in broadcast_channels.items():
        add_setting("broadcast_channels", guild_id, list(channels))

    # บันทึก notification_room
    for guild_id, channel_id in notification_room.items():
        add_setting("notification_room", guild_id, channel_id)

    # บันทึก notification_role
    for guild_id, role_id in notification_role.items():
        add_setting("notification_role", guild_id, role_id)

    # บันทึก bp_summary_room
    for guild_id, channel_id in bp_summary_room.items():
        add_setting("bp_summary_room", guild_id, channel_id)

    # บันทึก bp_reactions
    for guild_id, reactions in bp_reactions.items():
        add_setting("bp_reactions", guild_id, reactions)

    # บันทึก giveaway_room
    for guild_id, channel_id in giveaway_room.items():
        add_setting("giveaway_room", guild_id, channel_id)

    # บันทึก winner_history
    for guild_id, history in winner_history.items():
        add_setting("winner_history", guild_id, history)

    # อัปเดต Google Sheets
    settings_data = [] # ✅ ใช้ settings_sheet จาก global scope
    settings_sheet.clear()  # ลบข้อมูลเก่า
    settings_sheet.update("A1", [["Key", "Guild ID", "Data"]] + settings_data)  # เขียนข้อมูลใหม่
# ------------------ Broadcast Management ------------------
def add_broadcast_channel(guild_id: str, channel_id: int):
    broadcast_channels.setdefault(guild_id, set()).add(channel_id)
    save_settings()  # 💾 บันทึกทุกครั้งที่แก้ไข

def remove_broadcast_channel(guild_id: str, channel_id: int):
    if guild_id in broadcast_channels and channel_id in broadcast_channels[guild_id]:
        broadcast_channels[guild_id].remove(channel_id)
        if not broadcast_channels[guild_id]:
            del broadcast_channels[guild_id]
        save_settings()  # 💾 บันทึกหลังลบ

def get_rooms(guild_id: str):
    """ดึงรายการ channel_id ของ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    return list(broadcast_channels.get(guild_id, []))
# ------------------ Notification Room Management ------------------
def set_notification_room(guild_id: str, channel_id: int):
    notification_room[guild_id] = channel_id
    save_settings()

def get_notification_room(guild_id: str):
    return notification_room.get(guild_id)
# ------------------ Notification Role Management ------------------
def set_notification_role(guild_id: str, role_id: int):
    """กำหนด role ที่จะถูก mention เมื่อมีการแจ้งเตือน"""
    notification_role[guild_id] = role_id
    save_settings()  # 💾 บันทึกลง Google Sheets หลังแก้ไข

def get_notification_role(guild_id: str):
    """ดึง role ที่ใช้สำหรับแจ้งเตือน"""
    return notification_role.get(guild_id)