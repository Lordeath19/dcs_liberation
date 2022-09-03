from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import timedelta
from typing import Iterator, TYPE_CHECKING, List, Set, Dict

from game.ato import Package
from game.ato.flighttype import FlightType
from game.ato.traveltime import TotEstimator
from game.settings.settings import MINIMUM_MISSION_DURATION
from game.theater import MissionTarget

if TYPE_CHECKING:
    from game.coalition import Coalition


class MissionScheduler:
    def __init__(self, coalition: Coalition, desired_mission_length: timedelta) -> None:
        self.coalition = coalition
        self.desired_mission_length = desired_mission_length
        self.auto_asap_all = desired_mission_length == timedelta(
            minutes=MINIMUM_MISSION_DURATION
        )

    def all_packages_of_type(self, types: Set[FlightType]) -> List[Package]:
        return [
            package
            for package in self.coalition.ato.packages
            if package.primary_task in types
        ]

    def schedule_missions(self) -> None:
        """Identifies and plans mission for the turn."""

        def start_time_generator(
            count: int, earliest: int, latest: int, margin: int
        ) -> Iterator[timedelta]:
            interval = (latest - earliest) // count
            for time in range(earliest, latest, interval):
                error = random.randint(-margin, margin)
                yield timedelta(seconds=max(0, time + error))

        theater_types = {
            FlightType.AEWC,
        }

        dca_types = {
            FlightType.BARCAP,
            FlightType.TARCAP,
        }

        aa_types = {
            FlightType.DEAD,
            FlightType.SEAD,
        }

        oca_types = {
            FlightType.AIR_ASSAULT,
            FlightType.OCA_RUNWAY,
            FlightType.OCA_AIRCRAFT,
            FlightType.SWEEP,
        }

        previous_cap_end_time: Dict[MissionTarget, timedelta] = defaultdict(timedelta)
        non_dca_packages = [
            p for p in self.coalition.ato.packages if p.primary_task not in dca_types
        ]

        start_time = start_time_generator(
            count=len(non_dca_packages),
            earliest=5 * 60,
            latest=int(self.desired_mission_length.total_seconds()),
            margin=5 * 60,
        )
        ato_sequence = (
            self.all_packages_of_type(theater_types)
            + self.all_packages_of_type(aa_types)
            + self.all_packages_of_type(oca_types)
        )

        remainder_sequence = [
            package
            for package in self.coalition.ato.packages
            if package not in ato_sequence
        ]

        # Add rest of packages to ato_sequence
        ato_sequence.extend(remainder_sequence)
        for package in ato_sequence:
            tot = TotEstimator(package).earliest_tot()
            if package.primary_task in dca_types:
                previous_end_time = previous_cap_end_time[package.target]
                if tot > previous_end_time:
                    # Can't get there exactly on time, so get there ASAP. This
                    # will typically only happen for the first CAP at each
                    # target.
                    package.time_over_target = tot
                else:
                    package.time_over_target = previous_end_time

                departure_time = package.mission_departure_time
                # Should be impossible for CAPs
                if departure_time is None:
                    logging.error(f"Could not determine mission end time for {package}")
                    continue
                previous_cap_end_time[package.target] = departure_time
            elif package.auto_asap or self.auto_asap_all:
                package.set_tot_asap()
            else:
                # But other packages should be spread out a bit. Note that take
                # times are delayed, but all aircraft will become active at
                # mission start. This makes it more worthwhile to attack enemy
                # airfields to hit grounded aircraft, since they're more likely
                # to be present. Runway and air started aircraft will be
                # delayed until their takeoff time by AirConflictGenerator.
                package.time_over_target = next(start_time) + tot
