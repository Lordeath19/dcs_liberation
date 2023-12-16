from __future__ import annotations

from typing import TYPE_CHECKING

import luadata
from dcs.terrain import Airport
from dcs.terrain.terrain import Warehouses

from game.data.weapons import WeaponWSType

if TYPE_CHECKING:
    pass

COMBINED_ARMS_SLOTS = 1
AIRPORTS = "airports"
WEAPONS = "weapons"
UNLIMITED_MUNITIONS = "unlimitedMunitions"
WSTYPE = "wsType"
INITIAL_AMOUNT = "initialAmount"


class Warehouse:
    def __init__(self, warehouses: Warehouses) -> None:
        self.warehouses = warehouses

    def add_to_warehouse(
        self, airports: list[Airport], weapons: list[WeaponWSType]
    ) -> None:
        modded_warehouses = luadata.unserialize(
            str(self.warehouses), encoding="utf-8", multival=False
        )
        for airport in airports:
            modded_warehouses[AIRPORTS][airport.id][UNLIMITED_MUNITIONS] = False
            for weapon in weapons:
                weapon_dict = modded_warehouses[AIRPORTS][airport.id][WEAPONS]
                weapon_dict.append(
                    {
                        WSTYPE: [
                            weapon.wstype_1,
                            weapon.wstype_2,
                            weapon.wstype_3,
                            weapon.wstype_4,
                        ],
                        INITIAL_AMOUNT: 1000,
                    }
                )
        self.warehouses = "warehouses=\n" + luadata.serialize(
            modded_warehouses, encoding="utf-8", indent="\t", indent_level=2
        )
