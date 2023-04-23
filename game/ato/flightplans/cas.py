from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Type

from dcs import Point

from game.theater import FrontLine, TheaterGroundObject
from game.utils import Distance, Speed, kph, meters
from .ibuilder import IBuilder
from .invalidobjectivelocation import InvalidObjectiveLocation
from .patrolling import PatrollingFlightPlan, PatrollingLayout
from .uizonedisplay import UiZone, UiZoneDisplay
from .waypointbuilder import WaypointBuilder
from ..flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from ..flightwaypoint import FlightWaypoint


@dataclass(frozen=True)
class CasLayout(PatrollingLayout):
    target: FlightWaypoint

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield self.departure
        yield from self.nav_to
        yield self.patrol_start
        yield self.target
        yield self.patrol_end
        yield from self.nav_from
        yield self.arrival
        try:
            if self.reset is not None:
                yield self.reset
        except AttributeError:
            ...
        if self.divert is not None:
            yield self.divert
        yield self.bullseye


class CasFlightPlan(PatrollingFlightPlan[CasLayout], UiZoneDisplay):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def patrol_duration(self) -> timedelta:
        return self.flight.coalition.doctrine.cas_duration

    @property
    def patrol_speed(self) -> Speed:
        # 2021-08-02: patrol_speed will currently have no effect because
        # CAS doesn't use OrbitAction. But all PatrollingFlightPlan are expected
        # to have patrol_speed
        return kph(0)

    @property
    def engagement_distance(self) -> Distance:
        from game.missiongenerator.frontlineconflictdescription import FRONTLINE_LENGTH

        return meters(FRONTLINE_LENGTH) / 2

    @property
    def combat_speed_waypoints(self) -> set[FlightWaypoint]:
        return {self.layout.patrol_start, self.layout.target, self.layout.patrol_end}

    def request_escort_at(self) -> FlightWaypoint | None:
        return self.layout.patrol_start

    def dismiss_escort_at(self) -> FlightWaypoint | None:
        return self.layout.patrol_end

    def ui_zone(self) -> UiZone:
        return UiZone(
            [self.layout.target.position],
            self.engagement_distance,
        )


class Builder(IBuilder[CasFlightPlan, CasLayout]):
    def zone(self) -> tuple[Point, Point, Point]:
        assert self.package.waypoints
        return (
            self.package.waypoints.ingress,
            self.package.target.position,
            self.package.waypoints.split,
        )

    def frontline(self) -> tuple[Point, Point, Point]:
        from game.missiongenerator.frontlineconflictdescription import (
            FrontLineConflictDescription,
        )

        assert isinstance(self.package.target, FrontLine)
        bounds = FrontLineConflictDescription.frontline_bounds(
            self.package.target, self.theater
        )
        ingress = bounds.left_position
        center = bounds.center
        egress = bounds.right_position

        ingress_distance = ingress.distance_to_point(self.flight.departure.position)
        egress_distance = egress.distance_to_point(self.flight.departure.position)
        if egress_distance < ingress_distance:
            ingress, egress = egress, ingress
        return ingress, center, egress

    def layout(self) -> CasLayout:
        location = self.package.target

        if isinstance(location, FrontLine):
            ingress, center, egress = self.frontline()
        elif isinstance(location, TheaterGroundObject):
            ingress, center, egress = self.zone()
        else:
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        builder = WaypointBuilder(self.flight, self.coalition)

        is_helo = self.flight.unit_type.dcs_unit_type.helicopter
        ingress_egress_altitude = (
            self.doctrine.ingress_altitude if not is_helo else meters(50)
        )
        use_agl_ingress_egress = is_helo
        start = builder.ingress(FlightWaypointType.INGRESS_CAS, ingress, location)
        arrival, reset = builder.rearm(self.flight.arrival, start)

        return CasLayout(
            departure=builder.takeoff(self.flight.departure),
            nav_to=builder.nav_path(
                self.flight.departure.position,
                ingress,
                ingress_egress_altitude,
                use_agl_ingress_egress,
            ),
            nav_from=builder.nav_path(
                egress,
                self.flight.arrival.position,
                ingress_egress_altitude,
                use_agl_ingress_egress,
            ),
            patrol_start=start,
            target=builder.cas(center),
            patrol_end=builder.egress(egress, location),
            arrival=arrival,
            reset=reset,
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
        )

    def build(self) -> CasFlightPlan:
        return CasFlightPlan(self.flight, self.layout())
