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