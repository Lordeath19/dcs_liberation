from collections.abc import Iterator
from typing import Union

from game.commander.tasks.primitive.antiship import PlanAntiShip
from game.commander.tasks.primitive.dead import PlanDead
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method
from game.theater.theatergroundobject import IadsGroundObject, NavalGroundObject


class DegradeIads(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        threatening_radar_defenses = filter(
            lambda defense: defense.has_live_radar_sam, state.threatening_air_defenses
        )
        threatening_aaa_defenses = filter(
            lambda defense: not defense.has_live_radar_sam,
            state.threatening_air_defenses,
        )
        combined_defenses = list(threatening_radar_defenses) + list(
            threatening_aaa_defenses
        )

        for air_defense in combined_defenses:
            yield [self.plan_against(air_defense)]
        for detector in state.detecting_air_defenses:
            yield [self.plan_against(detector)]

    @staticmethod
    def plan_against(
        target: Union[IadsGroundObject, NavalGroundObject]
    ) -> Union[PlanDead, PlanAntiShip]:
        if isinstance(target, IadsGroundObject):
            return PlanDead(target)
        return PlanAntiShip(target)
