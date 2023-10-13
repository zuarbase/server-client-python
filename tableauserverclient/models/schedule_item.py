import xml.etree.ElementTree as ET
from datetime import datetime

from .interval_item import (
    IntervalItem,
    HourlyInterval,
    DailyInterval,
    WeeklyInterval,
    MonthlyInterval,
)
from .property_decorators import (
    property_is_enum,
    property_not_nullable,
    property_is_int,
)
from ..datetime_helpers import parse_datetime


class ScheduleItem(object):
    class Type:
        Extract = "Extract"
        Flow = "Flow"
        Subscription = "Subscription"
        DataAcceleration = "DataAcceleration"

    class ExecutionOrder:
        Parallel = "Parallel"
        Serial = "Serial"

    class State:
        Active = "Active"
        Suspended = "Suspended"

    def __init__(self, name, priority, schedule_type, execution_order, interval_item):
        self._created_at = None
        self._end_schedule_at = None
        self._id = None
        self._next_run_at = None
        self._state = None
        self._updated_at = None
        self.interval_item = interval_item
        self.execution_order = execution_order
        self.name = name
        self.priority = priority
        self.schedule_type = schedule_type

    def __repr__(self):
        return '<Schedule#{_id} "{_name}" {interval_item}>'.format(**self.__dict__)

    @property
    def created_at(self):
        return self._created_at

    @property
    def end_schedule_at(self):
        return self._end_schedule_at

    @property
    def execution_order(self):
        return self._execution_order

    @execution_order.setter
    @property_is_enum(ExecutionOrder)
    def execution_order(self, value):
        self._execution_order = value

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @name.setter
    #@property_not_nullable
    def name(self, value):
        self._name = value

    @property
    def next_run_at(self):
        return self._next_run_at

    @property
    def priority(self):
        return self._priority

    @priority.setter
    #@property_is_int(range=(1, 100))
    def priority(self, value):
        self._priority = value

    @property
    def schedule_type(self):
        return self._schedule_type

    @schedule_type.setter
    @property_is_enum(Type)
    #@property_not_nullable
    def schedule_type(self, value):
        self._schedule_type = value

    @property
    def state(self):
        return self._state

    @state.setter
    @property_is_enum(State)
    def state(self, value):
        self._state = value

    @property
    def updated_at(self):
        return self._updated_at

    @property
    def warnings(self):
        return self._warnings

    def _parse_common_tags(self, schedule_xml, ns):
        if not isinstance(schedule_xml, ET.Element):
            schedule_xml = ET.fromstring(schedule_xml).find(".//t:schedule", namespaces=ns)
        if schedule_xml is not None:
            (
                _,
                name,
                _,
                _,
                updated_at,
                _,
                next_run_at,
                end_schedule_at,
                execution_order,
                priority,
                interval_item,
            ) = self._parse_element(schedule_xml, ns)

            self._set_values(
                id_=None,
                name=name,
                state=None,
                created_at=None,
                updated_at=updated_at,
                schedule_type=None,
                next_run_at=next_run_at,
                end_schedule_at=end_schedule_at,
                execution_order=execution_order,
                priority=priority,
                interval_item=interval_item,
            )

        return self

    def _set_values(
        self,
        id_,
        name,
        state,
        created_at,
        updated_at,
        schedule_type,
        next_run_at,
        end_schedule_at,
        execution_order,
        priority,
        interval_item,
        warnings=None,
    ):
        if id_ is not None:
            self._id = id_
        if name:
            self._name = name
        if state:
            self._state = state
        if created_at:
            self._created_at = created_at
        if updated_at:
            self._updated_at = updated_at
        if schedule_type:
            self._schedule_type = schedule_type
        if next_run_at:
            self._next_run_at = next_run_at
        if end_schedule_at:
            self._end_schedule_at = end_schedule_at
        if execution_order:
            self._execution_order = execution_order
        if priority:
            self._priority = priority
        if interval_item:
            self._interval_item = interval_item
        if warnings:
            self._warnings = warnings

    @classmethod
    def from_response(cls, resp, ns):
        parsed_response = ET.fromstring(resp)
        return cls.from_element(parsed_response, ns)

    @classmethod
    def from_element(cls, parsed_response, ns):
        warnings = cls._read_warnings(parsed_response, ns)

        all_schedule_items = []
        all_schedule_xml = parsed_response.findall(".//t:schedule", namespaces=ns)
        for schedule_xml in all_schedule_xml:
            (
                id_,
                name,
                state,
                created_at,
                updated_at,
                schedule_type,
                next_run_at,
                end_schedule_at,
                execution_order,
                priority,
                interval_item,
            ) = cls._parse_element(schedule_xml, ns)

            schedule_item = cls(name, priority, schedule_type, execution_order, interval_item)

            schedule_item._set_values(
                id_=id_,
                name=None,
                state=state,
                created_at=created_at,
                updated_at=updated_at,
                schedule_type=None,
                next_run_at=next_run_at,
                end_schedule_at=end_schedule_at,
                execution_order=None,
                priority=None,
                interval_item=None,
                warnings=warnings,
            )

            all_schedule_items.append(schedule_item)
        return all_schedule_items

    @staticmethod
    def _parse_interval_item(parsed_response, frequency, ns):
        start_time = parsed_response.get("start", None)
        start_time = datetime.strptime(start_time, "%H:%M:%S").time()
        end_time = parsed_response.get("end", None)
        if end_time is not None:
            end_time = datetime.strptime(end_time, "%H:%M:%S").time()
        interval_elems = parsed_response.findall(".//t:intervals/t:interval", namespaces=ns)
        interval = []
        for interval_elem in interval_elems:
            interval.extend(interval_elem.attrib.items())

        if frequency == IntervalItem.Frequency.Daily:
            return DailyInterval(start_time)

        if frequency == IntervalItem.Frequency.Hourly:
            interval_occurrence, interval_value = interval.pop()

            # We use fractional hours for the two minute-based intervals.
            # Need to convert to hours from minutes here
            if interval_occurrence == IntervalItem.Occurrence.Minutes:
                interval_value = float(interval_value) / 60

            if interval_occurrence == IntervalItem.Occurrence.WeekDay:
                # ZS-8081 / TSC-4
                #
                # Magically, on 2023-10-10, customer Tableau Extract jobs started
                # failing like this:
                #
                #    File ".../tableauserverclient/models/interval_item.py", line 66, in interval
                #      if float(interval) not in VALID_INTERVALS:
                #    ValueError: could not convert string to float: 'Saturday'
                #
                # This is because the 'HourlyInterval' implementation does not
                # support a 'weekDay' parameter.  It appears that prior to
                # 2023-10-10, either of two things were happening:
                #    a. The API was not returning 'weekDay' and that, on
                #       that day, it began doing so.
                #    b. Prior to that day, 'frequency' was 'Frequency.Weekly'
                #       which would have allowed processing without error.
                #
                # Implementing support for 'weekDay' in 'HourlyInterval' is out of
                # scope for Zuar.  Because we never actually use any of the values
                # / parameters of extracts, this fix/hack ignores the 'weekDay'
                # when creating the 'HourlyInterval'.  It is sufficient to get Runner
                # extract jobs working again.
                #
                # Explanation of workaround:
                # The XML response that causes problems might look like this:
                # <task>
		#    <extractRefresh id="3b4af880-bc6b-44da-b1b4-f0dd0483f527" priority="50" consecutiveFailedCount="5" type="RefreshExtractTask">
		#       <schedule frequency="Hourly" nextRunAt="2023-10-13T01:30:00Z">
		#          <frequencyDetails start="02:30:00" end="02:30:00">
		#             <intervals>
		#                <interval hours="4" />
		#                <interval weekDay="Sunday" />
		#                <interval weekDay="Friday" />
		#             </intervals>
		#          </frequencyDetails>
		#       </schedule>
		#       <workbook id="465233e2-213f-4399-a1fa-7d3b058f9122" />
		#    </extractRefresh>
		# </task>
                # 'interval[]' will contain all intervals, in this case, all three intervals above.
                # interval[0] apparently will always be the first one with the 'hours="n"'.
                # If len(interval) > 1, the remainder will be the 'weekDay' intervals.
                # Since we really don't care at all about the intervals, but the fist one is
                # required to create the instance of HourlyInterval, we just ignore the values interval[1:].
                # This allows us to successfully create an HourlyInterval with the info needed
                # for Runner to execute the extract refresh.
                interval_occurrence, interval_value = interval[0]

            return HourlyInterval(start_time, end_time, interval_value)

        if frequency == IntervalItem.Frequency.Weekly:
            interval_values = [i[1] for i in interval]
            return WeeklyInterval(start_time, *interval_values)

        if frequency == IntervalItem.Frequency.Monthly:
            interval_occurrence, interval_value = interval.pop()
            return MonthlyInterval(start_time, interval_value)

    @staticmethod
    def _parse_element(schedule_xml, ns):
        id = schedule_xml.get("id", None)
        name = schedule_xml.get("name", None)
        state = schedule_xml.get("state", None)
        created_at = parse_datetime(schedule_xml.get("createdAt", None))
        updated_at = parse_datetime(schedule_xml.get("updatedAt", None))
        schedule_type = schedule_xml.get("type", None)
        frequency = schedule_xml.get("frequency", None)
        next_run_at = parse_datetime(schedule_xml.get("nextRunAt", None))
        end_schedule_at = parse_datetime(schedule_xml.get("endScheduleAt", None))
        execution_order = schedule_xml.get("executionOrder", None)

        priority = schedule_xml.get("priority", None)
        if priority:
            priority = int(priority)

        interval_item = None
        frequency_detail_elem = schedule_xml.find(".//t:frequencyDetails", namespaces=ns)
        if frequency_detail_elem is not None:
            interval_item = ScheduleItem._parse_interval_item(frequency_detail_elem, frequency, ns)

        return (
            id,
            name,
            state,
            created_at,
            updated_at,
            schedule_type,
            next_run_at,
            end_schedule_at,
            execution_order,
            priority,
            interval_item,
        )

    @staticmethod
    def parse_add_to_schedule_response(response, ns):
        parsed_response = ET.fromstring(response.content)
        warnings = ScheduleItem._read_warnings(parsed_response, ns)
        all_task_xml = parsed_response.findall(".//t:task", namespaces=ns)

        error = (
            "Status {}: {}".format(response.status_code, response.reason)
            if response.status_code < 200 or response.status_code >= 300
            else None
        )
        task_created = len(all_task_xml) > 0
        return error, warnings, task_created

    @staticmethod
    def _read_warnings(parsed_response, ns):
        all_warning_xml = parsed_response.findall(".//t:warning", namespaces=ns)
        warnings = list() if len(all_warning_xml) > 0 else None
        for warning_xml in all_warning_xml:
            warnings.append(warning_xml.get("message", None))
        return warnings
