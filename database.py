# import json

# กำหนดตัวแปรฐานข้อมูลให้เป็น dictionary ว่างก่อน
broadcast_channels = {}
notification_room = {}
notification_role = {}
boss_notifications = {}  # เพิ่มตัวแปรสำหรับจัดการแจ้งเตือนบอส
# ------------------ Save / Load functions ------------------
# ------------------ Broadcast management ------------------
def add_broadcast_channel(guild_id: str, channel_id: int):
    """เพิ่มช่องสำหรับ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    if guild_id not in broadcast_channels:
        broadcast_channels[guild_id] = set()
    broadcast_channels[guild_id].add(channel_id)

def remove_broadcast_channel(guild_id: str, channel_id: int):
    """ลบช่องออกจาก broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    if guild_id in broadcast_channels and channel_id in broadcast_channels[guild_id]:
        broadcast_channels[guild_id].remove(channel_id)
        if not broadcast_channels[guild_id]:
            del broadcast_channels[guild_id]  # ลบ key ถ้าเซิร์ฟเวอร์นั้นไม่มีช่องเหลืออยู่

def get_rooms(guild_id: str):
    """ดึงรายการ channel_id ของ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    return list(broadcast_channels.get(guild_id, []))

# ------------------ Notification Room Management ------------------
def set_notification_room(guild_id: str, channel_id: int):
    """กำหนดห้องแจ้งเตือนของบอส"""
    notification_room[guild_id] = channel_id

def get_notification_room(guild_id: str):
    """ดึงห้องแจ้งเตือนของบอส"""
    return notification_room.get(guild_id)

# ------------------ Notification Role Management ------------------
def set_notification_role(guild_id: str, role_id: int):
    """กำหนด role ที่จะถูก mention เมื่อมีการแจ้งเตือน"""
    notification_role[guild_id] = role_id

def get_notification_role(guild_id: str):
    """ดึง role ที่ใช้สำหรับแจ้งเตือน"""
    return notification_role.get(guild_id)