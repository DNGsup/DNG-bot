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

# ใช้ dictionary หรือ database ตามที่คุณใช้เก็บค่าห้องบอร์ดแคสต์
broadcast_rooms = {}

def add_broadcast_channel(guild_id: str, channel_id: int):
    if guild_id not in broadcast_rooms:
        broadcast_rooms[guild_id] = set()
    broadcast_rooms[guild_id].add(channel_id)

def remove_broadcast_channel(guild_id: str, channel_id: int):
    if guild_id in broadcast_rooms and channel_id in broadcast_rooms[guild_id]:
        broadcast_rooms[guild_id].remove(channel_id)
