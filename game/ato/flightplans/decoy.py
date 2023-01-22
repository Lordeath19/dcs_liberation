from __future__ import annotations

from datetime import timedelta
from typing import Type
from game.utils import Distance, meters

from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from ..flightwaypointtype import FlightWaypointType


class DecoyFlightPlan(FormationAttackFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def lead_time(self) -> timedelta:
        return timedelta(minutes=1)


class Builder(FormationAttackBuilder[DecoyFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        built_attack_plan = self._build(FlightWaypointType.INGRESS_DECOY)
        # Increase decoy range by increasing the altitude by 3000 metres
        built_attack_plan.ingress.alt = min(
            built_attack_plan.ingress.alt + Distance(3000), Distance(10000)
        )
        # To prevent the AI from loitering around the SAM site aimlessly, remove their waypoints
        for target in built_attack_plan.targets:
            target.only_for_player = True
        return built_attack_plan

    def build(self) -> DecoyFlightPlan:
        return DecoyFlightPlan(self.flight, self.layout())
