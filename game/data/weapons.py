from __future__ import annotations

import csv
import datetime
import inspect
import logging
from dataclasses import dataclass, field
from enum import unique, Enum
from functools import cached_property
from pathlib import Path
from typing import Iterator, Optional, Any, ClassVar

import yaml
from dcs.unitgroup import FlyingGroup
from dcs.weapons_data import weapon_ids, Weapons

from game.dcs.aircrafttype import AircraftType

PydcsWeapon = Any
PydcsWeaponAssignment = tuple[int, PydcsWeapon]


@dataclass(frozen=True)
class Weapon:
    """Wrapper for DCS weapons."""

    #: The CLSID used by DCS.
    clsid: str

    #: The group this weapon belongs to.
    weapon_group: WeaponGroup = field(compare=False)

    _by_clsid: ClassVar[dict[str, Weapon]] = {}
    _loaded: ClassVar[bool] = False

    def __str__(self) -> str:
        return self.name

    @cached_property
    def pydcs_data(self) -> PydcsWeapon:
        if self.clsid == "<CLEAN>":
            # Special case for a "weapon" that isn't exposed by pydcs.
            return {
                "clsid": self.clsid,
                "name": "Clean",
                "weight": 0,
            }
        return weapon_ids[self.clsid]

    @property
    def name(self) -> str:
        return self.pydcs_data["name"]

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Update any existing models with new data on load.
        try:
            updated = Weapon.with_clsid(state["clsid"])
            state.update(updated.__dict__)
            self.__dict__.update(state)
        except KeyError:
            pass

    @classmethod
    def register(cls, weapon: Weapon) -> None:
        if weapon.clsid in cls._by_clsid:
            duplicate = cls._by_clsid[weapon.clsid]
            raise ValueError(
                "Weapon CLSID used in more than one weapon type: "
                f"{duplicate.name} and {weapon.name}: {weapon.clsid}"
            )
        cls._by_clsid[weapon.clsid] = weapon

    @classmethod
    def with_clsid(cls, clsid: str) -> Weapon:
        if not cls._loaded:
            cls._load_all()
        return cls._by_clsid[clsid]

    @classmethod
    def _load_all(cls) -> None:
        WeaponGroup.load_all()
        cls._loaded = True

    def available_on(self, date: datetime.date) -> bool:
        introduction_year = self.weapon_group.introduction_year
        if introduction_year is None:
            return True
        return date >= datetime.date(introduction_year, 1, 1)

    @property
    def fallbacks(self) -> Iterator[Weapon]:
        yield self
        fallback: Optional[WeaponGroup] = self.weapon_group
        while fallback is not None:
            yield from fallback.weapons
            fallback = fallback.fallback


@unique
class WeaponType(Enum):
    ARM = "ARM"
    LGB = "LGB"
    TGP = "TGP"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class WeaponGroup:
    """Group of "identical" weapons loaded from resources/weapons.

    DCS has multiple unique "weapons" for each type of weapon. There are four distinct
    class IDs for the AIM-7M, some unique to certain aircraft. We group them in the
    resources to make year/fallback data easier to track.
    """

    #: The name of the weapon group in the resource file.
    name: str

    #: The type of the weapon group.
    type: WeaponType = field(compare=False)

    #: The year of introduction.
    introduction_year: Optional[int] = field(compare=False)

    #: The name of the fallback weapon group.
    fallback_name: Optional[str] = field(compare=False)

    #: The specific weapons that belong to this weapon group.
    weapons: list[Weapon] = field(init=False, default_factory=list)

    _by_name: ClassVar[dict[str, WeaponGroup]] = {}
    _loaded: ClassVar[bool] = False

    def __str__(self) -> str:
        return self.name

    @property
    def fallback(self) -> Optional[WeaponGroup]:
        if self.fallback_name is None:
            return None
        return WeaponGroup.named(self.fallback_name)

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Update any existing models with new data on load.
        updated = WeaponGroup.named(state["name"])
        state.update(updated.__dict__)
        self.__dict__.update(state)

    @classmethod
    def register(cls, group: WeaponGroup) -> None:
        if group.name in cls._by_name:
            duplicate = cls._by_name[group.name]
            raise ValueError(
                "Weapon group name used in more than one weapon type: "
                f"{duplicate.name} and {group.name}"
            )
        cls._by_name[group.name] = group

    @classmethod
    def named(cls, name: str) -> WeaponGroup:
        if not cls._loaded:
            cls.load_all()
        return cls._by_name[name]

    @classmethod
    def _each_weapon_group(cls) -> Iterator[WeaponGroup]:
        for group_file_path in Path("resources/weapons").glob("**/*.yaml"):
            with group_file_path.open(encoding="utf8") as group_file:
                data = yaml.safe_load(group_file)
            name = data["name"]
            try:
                weapon_type = WeaponType(data["type"])
            except KeyError:
                weapon_type = WeaponType.UNKNOWN
            year = data.get("year")
            fallback_name = data.get("fallback")
            group = WeaponGroup(name, weapon_type, year, fallback_name)
            for clsid in data["clsids"]:
                weapon = Weapon(clsid, group)
                Weapon.register(weapon)
                group.weapons.append(weapon)
            yield group

    @classmethod
    def register_clean_pylon(cls) -> None:
        group = WeaponGroup(
            "Clean pylon",
            type=WeaponType.UNKNOWN,
            introduction_year=None,
            fallback_name=None,
        )
        cls.register(group)
        weapon = Weapon("<CLEAN>", group)
        Weapon.register(weapon)
        group.weapons.append(weapon)

    @classmethod
    def register_unknown_weapons(cls, seen_clsids: set[str]) -> None:
        unknown_weapons = set(weapon_ids.keys()) - seen_clsids
        group = WeaponGroup(
            "Unknown",
            type=WeaponType.UNKNOWN,
            introduction_year=None,
            fallback_name=None,
        )
        cls.register(group)
        for clsid in unknown_weapons:
            weapon = Weapon(clsid, group)
            Weapon.register(weapon)
            group.weapons.append(weapon)

    @classmethod
    def load_all(cls) -> None:
        if cls._loaded:
            return
        seen_clsids: set[str] = set()
        for group in cls._each_weapon_group():
            cls.register(group)
            seen_clsids.update(w.clsid for w in group.weapons)
        cls.register_clean_pylon()
        cls.register_unknown_weapons(seen_clsids)
        cls._loaded = True


@dataclass(frozen=True)
class Pylon:
    number: int
    allowed: set[Weapon]

    def can_equip(self, weapon: Weapon) -> bool:
        # TODO: Fix pydcs to support the <CLEAN> "weapon".
        # <CLEAN> is a special case because pydcs doesn't know about that "weapon", so
        # it's not compatible with *any* pylon. Just trust the loadout and try to equip
        # it.
        #
        # A similar hack exists in QPylonEditor to forcibly add "Clean" to the list of
        # valid configurations for that pylon if a loadout has been seen with that
        # configuration.
        return weapon in self.allowed or weapon.clsid == "<CLEAN>"

    def equip(self, group: FlyingGroup[Any], weapon: Weapon) -> None:
        if not self.can_equip(weapon):
            logging.error(f"Pylon {self.number} cannot equip {weapon.name}")
        group.load_pylon(self.make_pydcs_assignment(weapon), self.number)

    def make_pydcs_assignment(self, weapon: Weapon) -> PydcsWeaponAssignment:
        return self.number, weapon.pydcs_data

    def available_on(self, date: datetime.date) -> Iterator[Weapon]:
        for weapon in self.allowed:
            if weapon.available_on(date):
                yield weapon

    @classmethod
    def for_aircraft(cls, aircraft: AircraftType, number: int) -> Pylon:
        # In pydcs these are all arbitrary inner classes of the aircraft type.
        # The only way to identify them is by their name.
        pylons = [
            v
            for v in aircraft.dcs_unit_type.__dict__.values()
            if inspect.isclass(v) and v.__name__.startswith("Pylon")
        ]

        # And that Pylon class has members with irrelevant names that have
        # values of (pylon number, allowed weapon).
        allowed = set()
        for pylon in pylons:
            for key, value in pylon.__dict__.items():
                if key.startswith("__"):
                    continue
                pylon_number, weapon = value
                if pylon_number != number:
                    continue
                allowed.add(Weapon.with_clsid(weapon["clsid"]))

        return cls(number, allowed)

    @classmethod
    def iter_pylons(cls, aircraft: AircraftType) -> Iterator[Pylon]:
        for pylon in sorted(list(aircraft.dcs_unit_type.pylons)):
            yield cls.for_aircraft(aircraft, pylon)


@dataclass
class WeaponWSType:
    """Wrapper for DCS weapons."""

    #: Name of the weapon
    name: str

    #: WsTypes for dcs
    wstype_1: int
    wstype_2: int
    wstype_3: int
    wstype_4: int

    #: The CLSID used by DCS.
    clsids: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(obj: Any) -> WeaponWSType:
        _name = str(obj.get("name"))
        _wstype_1 = int(obj.get("wstype_1"))
        _wstype_2 = int(obj.get("wstype_2"))
        _wstype_3 = int(obj.get("wstype_3"))
        _wstype_4 = int(obj.get("wstype_4"))
        return WeaponWSType(_name, _wstype_1, _wstype_2, _wstype_3, _wstype_4)

    @staticmethod
    def get_wstypes() -> list[WeaponWSType]:
        dcs_weapons = list()
        with open(Path("resources/weapons/weapons.csv"), "r") as warehouse_data:
            reader = csv.DictReader(warehouse_data, delimiter=";")
            for weapon in reader:
                dcs_weapons.append(WeaponWSType.from_dict(weapon))
        return dcs_weapons

    @staticmethod
    def get_clsid_mapping() -> dict[str, str]:
        weapon_members = [
            attr
            for attr in dir(Weapons)
            if not callable(getattr(Weapons, attr)) and not attr.startswith("__")
        ]
        weapons_data = dict()
        for i in weapon_members:
            weapon = getattr(Weapons, i)
            weapons_data[weapon["name"].lower()] = weapon["clsid"]
        return weapons_data

    def get_clsids(self, filter_unregistered: bool = True) -> list[str]:
        weapon_data = self.get_clsid_mapping()
        weapon_names = [
            weapon_name
            for weapon_name in weapon_data.keys()
            if self.name.lower() in weapon_name.lower()
        ]
        clsids = [weapon_data[weapon_name] for weapon_name in weapon_names]
        if filter_unregistered:
            return self.filter_unregistered_weapons(clsids)
        return clsids

    def available_on(self, date: datetime.date) -> bool:
        weapons = self.weapon_with_clsid()
        if weapons is None:
            return False
        earliest_weapon = min(
            weapons,
            key=lambda weapon: weapon.weapon_group.introduction_year or float("inf"),
        )
        return earliest_weapon.available_on(date)

    def weapon_with_clsid(self) -> Optional[list[Weapon]]:
        return [Weapon.with_clsid(weapon_clsid) for weapon_clsid in self.clsids]

    @staticmethod
    def filter_unregistered_weapons(clsids: list[str]) -> list[str]:
        # At least one of the weapons are registered with an era limitation
        # remove non-limited weapons in group
        weapons = [Weapon.with_clsid(weapon_clsid) for weapon_clsid in clsids]
        if any(
            [
                weapon_object
                for weapon_object in weapons
                if weapon_object.weapon_group.introduction_year
            ]
        ):
            return [
                weapon_object.clsid
                for weapon_object in weapons
                if weapon_object.weapon_group.introduction_year
            ]
        return clsids

    @staticmethod
    def populate_weapons() -> list[WeaponWSType]:
        dcs_weapons = WeaponWSType.get_wstypes()
        populated_weapons = list()
        for dcs_weapon in dcs_weapons:
            dcs_weapon.clsids = dcs_weapon.get_clsids()
            if dcs_weapon.clsids:
                populated_weapons.append(dcs_weapon)
        return populated_weapons
