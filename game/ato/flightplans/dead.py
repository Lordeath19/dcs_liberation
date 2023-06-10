from __future__ import annotations

import logging
from typing import Type

from game.theater.theatergroundobject import (
    EwrGroundObject,
    SamGroundObject,
    TheaterGroundObject,
)
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .invalidobjectivelocation import InvalidObjectiveLocation
from .. import FlightType
from ..flightwaypointtype import FlightWaypointType
from ..loadouts import Loadout


class DeadFlightPlan(FormationAttackFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(FormationAttackBuilder[DeadFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        location = self.package.target

        is_ewr = isinstance(location, EwrGroundObject)
        is_sam = isinstance(location, SamGroundObject)
        if (not is_ewr and not is_sam) or not isinstance(location, TheaterGroundObject):
            logging.exception(
                f"Invalid Objective Location for DEAD flight {self.flight=} at "
                f"{location=}"
            )
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        # There is no need to use DEAD when you can use STRIKE as this is just AAA
        if not location.has_live_radar_sam:
            self.flight.loadout = Loadout.default_for_task_and_aircraft(
                FlightType.CAS, self.flight.unit_type.dcs_unit_type
            )

        return self._build(FlightWaypointType.INGRESS_DEAD)

    def build(self) -> DeadFlightPlan:
        return DeadFlightPlan(self.flight, self.layout())
