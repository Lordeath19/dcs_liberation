from typing import Any, Sequence

from dcs import Mission
from dcs.action import AITaskPush
from dcs.condition import TimeSinceFlag
from dcs.task import SwitchWaypoint, WrappedAction
from dcs.triggers import TriggerCondition, Event, TriggerRule
from dcs.unitgroup import FlyingGroup

from game.ato import Flight, FlightWaypoint


def stop_orbit_action(
    waypoint: FlightWaypoint,
    trigger: TriggerRule,
    flight: Flight,
    group: FlyingGroup[Any],
) -> None:
    waypoints = flight.flight_plan.waypoints

    # All waypoints start from an INIT waypoint, so advance the index by one as flight plans don't account for it
    switch_waypoint_task = SwitchWaypoint(
        waypoints.index(waypoint) + 1, waypoints.index(waypoint) + 2
    )
    if is_action_exists(group.tasks, switch_waypoint_task):
        return

    group.add_trigger_action(switch_waypoint_task)
    stop_action = AITaskPush(group.id, len(group.tasks))
    trigger.add_action(stop_action)


def is_action_exists(
    tasks: Sequence[WrappedAction], task_to_check: WrappedAction
) -> bool:
    return any(
        task
        for task in tasks
        if task.Id == task_to_check.Id and task.params == task_to_check.params
    )


def create_stop_orbit_trigger(
    waypoint: FlightWaypoint,
    flight: Flight,
    group: FlyingGroup[Any],
    mission: Mission,
    elapsed: int,
) -> None:
    package_id = id(flight.package)
    orbits = [
        x
        for x in mission.triggerrules.triggers
        if x.comment == f"StopOrbit{package_id}"
    ]
    if not any(orbits):
        stop_trigger = TriggerCondition(Event.NoEvent, f"StopOrbit{package_id}")
        stop_condition = TimeSinceFlag(elapsed)
        # Get the waypoint to abort from
        stop_trigger.add_condition(stop_condition)
        stop_orbit_action(waypoint, stop_trigger, flight, group)
        mission.triggerrules.triggers.append(stop_trigger)
    else:
        for trigger in orbits:
            # Action already exists, safety measure against multiple stop conditions for same group
            stop_orbit_action(waypoint, trigger, flight, group)
