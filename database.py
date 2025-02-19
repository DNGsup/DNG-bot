import json

# กำหนดตัวแปรฐานข้อมูลให้เป็น dictionary ว่างก่อน
broadcast_channels = {}
notification_room = {}
notification_role = {}
boss_notifications = {}  # ไม่บันทึกลงไฟล์

# ------------------ Save / Load functions ------------------
# โหลดข้อมูลจากไฟล์
def load_data():
    global broadcast_channels, notification_room, notification_role
    try:
        with open("database.json", "r") as f:
            data = json.load(f)
            broadcast_channels = {k: set(v) for k, v in data.get("broadcast_channels", {}).items()}
            notification_room = data.get("notification_room", {})
            notification_role = data.get("notification_role", {})
    except (FileNotFoundError, json.JSONDecodeError):
        print("No existing data file. Starting fresh.")
        broadcast_channels = {}
        notification_room = {}
        notification_role = {}

# บันทึกข้อมูลลงไฟล์ (ยกเว้น boss_notifications)
def save_data():
    data = {
        "broadcast_channels": {k: list(v) for k, v in broadcast_channels.items()},
        "notification_room": notification_room,
        "notification_role": notification_role
    }
    with open("database.json", "w") as f:
        json.dump(data, f)

# ------------------ Broadcast management ------------------
def add_broadcast_channel(guild_id: str, channel_id: int):
    """เพิ่มช่องสำหรับ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    if guild_id not in broadcast_channels:
        broadcast_channels[guild_id] = set()
    broadcast_channels[guild_id].add(channel_id)
    save_data()  # บันทึกทุกครั้งที่มีการเปลี่ยนแปลง

def remove_broadcast_channel(guild_id: str, channel_id: int):
    """ลบช่องออกจาก broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    if guild_id in broadcast_channels and channel_id in broadcast_channels[guild_id]:
        broadcast_channels[guild_id].remove(channel_id)
        if not broadcast_channels[guild_id]:
            del broadcast_channels[guild_id]  # ลบ key ถ้าเซิร์ฟเวอร์นั้นไม่มีช่องเหลืออยู่
        save_data()

def get_rooms(guild_id: str):
    """ดึงรายการ channel_id ของ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    return list(broadcast_channels.get(guild_id, []))

# ------------------ Notification Room Management ------------------
def set_notification_room(guild_id: str, channel_id: int):
    """กำหนดห้องแจ้งเตือนของบอส"""
    notification_room[guild_id] = channel_id
    save_data()

def get_notification_room(guild_id: str):
    """ดึงห้องแจ้งเตือนของบอส"""
    return notification_room.get(guild_id)

# ------------------ Notification Role Management ------------------
def set_notification_role(guild_id: str, role_id: int):
    """กำหนด role ที่จะถูก mention เมื่อมีการแจ้งเตือน"""
    notification_role[guild_id] = role_id
    save_data()

def get_notification_role(guild_id: str):
    """ดึง role ที่ใช้สำหรับแจ้งเตือน"""
    return notification_role.get(guild_id)

load_data()  # โหลดข้อมูลจาก database.json เมื่อบอทเริ่มทำงาน