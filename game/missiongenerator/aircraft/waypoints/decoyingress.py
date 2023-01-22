import logging

from dcs.point import MovingPoint
from dcs.task import (
    AttackGroup,
    EngageGroup,
    Expend,
    OptECMUsing,
    WeaponType as DcsWeaponType,
)
from game.data.weapons import WeaponType

from game.theater import TheaterGroundObject
from .pydcswaypointbuilder import PydcsWaypointBuilder


class DecoyIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        self.register_special_waypoints(self.waypoint.targets)

        target = self.package.target
        if not isinstance(target, TheaterGroundObject):
            logging.error(
                "Unexpected target type for Decoy mission: %s",
                target.__class__.__name__,
            )
            return

        for group in target.groups:
            miz_group = self.mission.find_group(group.group_name)
            if miz_group is None:
                logging.error(
                    f"Could not find group for Decoy mission {group.group_name}"
                )
                continue

            # All non ARM types will use the normal AttackGroup Task
            attack_task = AttackGroup(
                miz_group.id,
                weapon_type=DcsWeaponType.Guided,
                group_attack=True,
                expend=Expend.All,
            )
            # Use if the group has decoys aboard
            if self.flight.loadout.has_weapon_of_type(WeaponType.UNKNOWN):
                attack_task.params["weaponType"] = DcsWeaponType.Decoy.value
            waypoint.tasks.append(attack_task)

        # Preemptively use ECM to better avoid getting swatted.
        ecm_option = OptECMUsing(value=OptECMUsing.Values.UseIfDetectedLockByRadar)
        waypoint.tasks.append(ecm_option)
