from __future__ import annotations

from dataclasses import dataclass, field

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.settings.settings import AutoAtoTasking
from game.theater import FrontLine
from game.ato.flighttype import FlightType


@dataclass
class PlanCas(PackagePlanningTask[FrontLine]):
    saturate: bool = field(default=False)
    minimal_tasking = AutoAtoTasking.Limited

    def assign_threatening_air_defenses(self, state: TheaterState) -> None:
        for iads_threat in self.iter_iads_threats(state):
            if iads_threat not in state.threatening_air_defenses:
                state.threatening_air_defenses.append(iads_threat)

    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.vulnerable_front_lines and not self.saturate:
            return False
        # Do not bother planning CAS when there are no enemy ground units at the front.
        # An exception is made for turn zero since that's not being truly planned, but
        # just to determine what missions should be planned on turn 1 (when there *will*
        # be ground units) and what aircraft should be ordered.
        enemy_cp = self.target.control_point_friendly_to(
            player=not state.context.coalition.player
        )
        # We don't really care about the preconditions and won't cancel the CAS.
        # But, do plan against SAMs threatening the CAS flight
        self.assign_threatening_air_defenses(state)
        if enemy_cp.deployable_front_line_units == 0 and state.context.turn > 0:
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        if not self.saturate:
            state.vulnerable_front_lines.remove(self.target)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.CAS, 2)
        if not self.saturate:
            self.propose_flight(FlightType.TARCAP, 2)
