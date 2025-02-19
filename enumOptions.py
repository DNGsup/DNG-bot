from enum import Enum

class BossName(Enum):
    LOWER_CAVE = "Lower Cave"
    CAVE_7 = "Cave 7"
    CAVE_8 = "Cave 8"
    CAVE_9 = "Cave 9"
    REGION_2 = "Region 2"
    REGION_3 = "Region 3"
    REGION_4 = "Region 4"
    RUINED_KNIGHT = "Ruined Knight"
    TANDALLON = "Tandallon"
    DERGIO = "Dergio"
    DUCAS = "Ducas"
    WORLD_DUNGEON = "World Dungeon"

class Owner(Enum):
    KNIGHT = "Knight"
    BISHOP = "Bishop"
    RF = "RF"

OWNER_ICONS = {
    "Knight": "💙",
    "Bishop": "💚",
    "RF": "💛"
}

class BroadcastSettingAction(Enum):
    ADD = "add"
    REMOVE = "remove"

class BroadcastMode(Enum):
    STANDARD = "standard"
    MULTI = "multi"
