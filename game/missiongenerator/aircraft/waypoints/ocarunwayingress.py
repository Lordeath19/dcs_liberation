import itertools
import logging
from random import choice, uniform
from typing import Iterable

from dcs import Point
from dcs.point import MovingPoint
from dcs.task import (
    Bombing,
    BombingRunway,
    OptFormation,
    WeaponType as DcsWeaponType,
)
from dcs.task import WeaponType

from game.data.weapons import WeaponType
from game.data.weapons import WeaponType as WeaponTypeEnum
from game.theater import Airfield
from game.utils import Distance, nautical_miles, meters
from .pydcswaypointbuilder import PydcsWaypointBuilder


class OcaRunwayIngressBuilder(PydcsWaypointBuilder):
    RUNWAY_LENGTH = nautical_miles(1)

    @staticmethod
    def get_runway_point(
        airfield: Airfield, deviation: Distance = meters(50)
    ) -> Iterable[Point]:
        distance_multiplier = 0.0
        full_distance = OcaRunwayIngressBuilder.RUNWAY_LENGTH.meters / 2
        position = airfield.position
        for runway in itertools.cycle(airfield.airport.runways):
            distance = distance_multiplier * full_distance
            distance_multiplier = min(1, distance_multiplier + 0.1)
            distance_from_center = uniform(-distance, distance)
            runway_heading = choice([runway.heading, runway.opposite.heading])
            position_on_runway = position.point_from_heading(
                runway_heading, distance_from_center
            )
            yield position_on_runway.random_point_within(deviation.meters)

    def add_strike_tasks(self, waypoint: MovingPoint) -> None:
        target = self.package.target
        assert isinstance(target, Airfield)
        for i, point in enumerate(self.get_runway_point(target)):
            if i > 30:
                return
            bombing = Bombing(
                point,
                weapon_type=WeaponType.Auto,
                group_attack=True,
            )
            waypoint.tasks.append(bombing)

    def add_tasks(self, waypoint: MovingPoint) -> None:
        target = self.package.target
        if not isinstance(target, Airfield):
            logging.error(
                "Unexpected target type for runway bombing mission: %s",
                target.__class__.__name__,
            )
            return
        if self.flight.any_member_has_weapon_of_type(WeaponTypeEnum.CRUISE):
            self.add_strike_tasks(waypoint)
        # The BombingRunway task in DCS does not use LGBs, which necessitates special handling
        # by using the Bombing task instead. See https://github.com/dcs-liberation/dcs_liberation/issues/894
        # for more details.
        # The LGB work around assumes the Airfield position in DCS is on a runway, which seems
        # to be the case for most if not all airfields.
        elif self.flight.any_member_has_weapon_of_type(WeaponType.LGB):
            waypoint.tasks.append(
                Bombing(
                    position=target.position,
                    group_attack=True,
                    weapon_type=DcsWeaponType.Guided,
                )
            )
        else:  # Use BombingRunway task for all other weapon types
            waypoint.tasks.append(
                BombingRunway(airport_id=target.airport.id, group_attack=True)
            )
        waypoint.tasks.append(OptFormation.trail_open())
