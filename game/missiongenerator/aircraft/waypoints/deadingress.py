import functools
import itertools
import logging
import operator

from dcs.point import MovingPoint
from dcs.task import AttackGroup, OptECMUsing, WeaponType, Bombing, Expend

from game.data.weapons import WeaponType as WeaponTypeEnum
from game.theater import TheaterGroundObject, TheaterUnit
from .pydcswaypointbuilder import PydcsWaypointBuilder


class DeadIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        self.register_special_waypoints(self.waypoint.targets)
        if self.flight.loadout.has_weapon_of_type(WeaponTypeEnum.CRUISE):
            self.add_strike_tasks(waypoint)
        else:
            self.add_attack_tasks(waypoint)

    def add_attack_tasks(self, waypoint: MovingPoint) -> None:
        target = self.package.target
        if not isinstance(target, TheaterGroundObject):
            logging.error(
                "Unexpected target type for DEAD mission: %s",
                target.__class__.__name__,
            )
            return

        for group in target.groups:
            miz_group = self.mission.find_group(group.group_name)
            if miz_group is None:
                logging.error(
                    f"Could not find group for DEAD mission {group.group_name}"
                )
                continue

            task = AttackGroup(
                miz_group.id, weapon_type=WeaponType.Auto, group_attack=True
            )
            waypoint.tasks.append(task)

        # Preemptively use ECM to better avoid getting swatted.
        ecm_option = OptECMUsing(value=OptECMUsing.Values.UseIfDetectedLockByRadar)
        waypoint.tasks.append(ecm_option)

    def add_strike_tasks(self, waypoint: MovingPoint) -> None:
        target_object = self.package.target
        if not isinstance(target_object, TheaterGroundObject):
            logging.error(
                "Unexpected target type for DEAD mission: %s",
                target_object.__class__.__name__,
            )
            return
        target_groups = target_object.groups
        target_units = [group.units for group in target_groups]
        targets: list[TheaterUnit] = list(
            functools.reduce(operator.iconcat, target_units, [])
        )
        targets = sorted(targets, key=lambda unit: unit.detection_range, reverse=True)
        for count, target in enumerate(itertools.cycle(targets)):
            # Place up to 30 bombing points, causing AI to expend all ammunition
            if count >= 30:
                return

            bombing = Bombing(
                target.position, weapon_type=WeaponType.Auto, group_attack=True
            )
            # If there is only one target, drop all ordnance in one pass.
            if len(self.waypoint.targets) == 1:
                bombing.params["expend"] = Expend.All.value
            waypoint.tasks.append(bombing)

            # Register special waypoints
            self.register_special_waypoints(self.waypoint.targets)
        # Preemptively use ECM to better avoid getting swatted.
        ecm_option = OptECMUsing(value=OptECMUsing.Values.UseIfDetectedLockByRadar)
        waypoint.tasks.append(ecm_option)
