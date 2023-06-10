from __future__ import annotations

from datetime import timedelta
from typing import Type

from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from ..flightwaypointtype import FlightWaypointType


class SeadFlightPlan(FormationAttackFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def lead_time(self) -> timedelta:
        return timedelta(minutes=1)


class Builder(FormationAttackBuilder[SeadFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        built_attack_plan = self._build(FlightWaypointType.INGRESS_SEAD)
        for target in built_attack_plan.targets:
            target.only_for_player = True
        return built_attack_plan

    def build(self) -> SeadFlightPlan:
        return SeadFlightPlan(self.flight, self.layout())
