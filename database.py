# database.py
broadcast_channels = {}
# เก็บข้อมูลห้องแจ้งเตือนและโรลแจ้งเตือน
notification_settings = {}
# เก็บข้อมูลการแจ้งเตือนบอส
boss_notifications = {}

# -------------------------------------------------------------------
def add_broadcast_channel(guild_id: str, channel_id: int):
    """เพิ่มช่องสำหรับ broadcast ในเซิร์ฟเวอร์ที่กำหนด (เก็บในหน่วยความจำเท่านั้น)"""
    if guild_id not in broadcast_channels:
        broadcast_channels[guild_id] = set()
    broadcast_channels[guild_id].add(channel_id)

def remove_broadcast_channel(guild_id: str, channel_id: int):
    """ลบช่องออกจาก broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    if guild_id in broadcast_channels and channel_id in broadcast_channels[guild_id]:
        broadcast_channels[guild_id].remove(channel_id)

def get_rooms(guild_id: str):
    """ดึงรายการ channel_id ของ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    return list(broadcast_channels.get(guild_id, []))
# -------------------------------------------------------------------
def set_notification_room(guild_id: str, channel_id: int):
    """ตั้งค่าห้องแจ้งเตือนบอส"""
    if guild_id not in notification_settings:
        notification_settings[guild_id] = {"room": None, "role": None}
    notification_settings[guild_id]["room"] = channel_id

def set_notification_role(guild_id: str, role_id: int):
    """ตั้งค่าโรลที่ต้องการให้แท็ก"""
    if guild_id not in notification_settings:
        notification_settings[guild_id] = {"room": None, "role": None}
    notification_settings[guild_id]["role"] = role_id

def add_boss_notification(guild_id: str, boss_name: str, hours: int, minutes: int, owner: str):
    """เพิ่มรายการแจ้งเตือนบอส"""
    if guild_id not in boss_notifications:
        boss_notifications[guild_id] = []
    spawn_time = (hours * 60) + minutes
    boss_notifications[guild_id].append({
        "boss_name": boss_name,
        "spawn_time": spawn_time,
        "owner": owner
    })
    boss_notifications[guild_id].sort(key=lambda x: x["spawn_time"])

def remove_boss_notification(guild_id: str, boss_name: str):
    """ลบรายการแจ้งเตือนบอส"""
    if guild_id in boss_notifications:
        boss_notifications[guild_id] = [b for b in boss_notifications[guild_id] if b["boss_name"] != boss_name]

def get_boss_notifications(guild_id: str):
    """ดึงรายการแจ้งเตือนบอส (สูงสุด 10 รายการ)"""
    return boss_notifications.get(guild_id, [])[:10]

def get_notification_settings(guild_id: str):
    """ดึงค่าห้องและโรลแจ้งเตือน"""
    return notification_settings.get(guild_id, {"room": None, "role": None})
# -------------------------------------------------------------------
