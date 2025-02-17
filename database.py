import json

DATABASE_FILE = "database.json"

class Database:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        try:
            with open(DATABASE_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"broadcast_rooms": []}

    def save_data(self):
        with open(DATABASE_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_room(self, room_name):
        if room_name not in self.data["broadcast_rooms"]:
            self.data["broadcast_rooms"].append(room_name)
            self.save_data()
            return True
        return False

    def remove_room(self, room_name):
        if room_name in self.data["broadcast_rooms"]:
            self.data["broadcast_rooms"].remove(room_name)
            self.save_data()
            return True
        return False

    def get_rooms(self):
        return self.data["broadcast_rooms"]

db = Database()

# เพิ่มให้เก็บข้อมูลเป็น dict โดยใช้ guild_id เป็น key
broadcast_channels = {}

def add_broadcast_channel(guild_id: str, channel_id: int):
    if guild_id not in broadcast_channels:
        broadcast_channels[guild_id] = set()
    broadcast_channels[guild_id].add(channel_id)

def remove_broadcast_channel(guild_id: str, channel_id: int):
    if guild_id in broadcast_channels and channel_id in broadcast_channels[guild_id]:
        broadcast_channels[guild_id].remove(channel_id)

def get_rooms(guild_id: str):
    return list(broadcast_channels.get(guild_id, []))  # คืนค่าลิสต์ห้องที่ตั้งค่าไว้
