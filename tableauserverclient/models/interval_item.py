from .property_decorators import property_is_valid_time, property_not_nullable


class IntervalItem(object):
    class Frequency:
        Hourly = "Hourly"
        Daily = "Daily"
        Weekly = "Weekly"
        Monthly = "Monthly"

    class Occurrence:
        Minutes = "minutes"
        Hours = "hours"
        WeekDay = "weekDay"
        MonthDay = "monthDay"

    class Day:
        Sunday = "Sunday"
        Monday = "Monday"
        Tuesday = "Tuesday"
        Wednesday = "Wednesday"
        Thursday = "Thursday"
        Friday = "Friday"
        Saturday = "Saturday"
        LastDay = "LastDay"


class HourlyInterval(object):
    def __init__(self, start_time, end_time, interval_value):

        self.start_time = start_time
        self.end_time = end_time
        self.interval = interval_value

    @property
    def _frequency(self):
        return IntervalItem.Frequency.Hourly

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    @property_is_valid_time
    @property_not_nullable
    def start_time(self, value):
        self._start_time = value

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    @property_is_valid_time
    @property_not_nullable
    def end_time(self, value):
        self._end_time = value

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, interval):
        VALID_INTERVALS = {0.25, 0.5, 1, 2, 4, 6, 8, 12}
        if float(interval) not in VALID_INTERVALS:
            error = "Invalid interval {} not in {}".format(interval, str(VALID_INTERVALS))
            raise ValueError(error)

        self._interval = interval

    def _interval_type_pairs(self):

        # We use fractional hours for the two minute-based intervals.
        # Need to convert to minutes from hours here
        if self.interval in {0.25, 0.5}:
            calculated_interval = int(self.interval * 60)
            interval_type = IntervalItem.Occurrence.Minutes
        else:
            calculated_interval = self.interval
            interval_type = IntervalItem.Occurrence.Hours

        return [(interval_type, str(calculated_interval))]


class DailyInterval(object):
    def __init__(self, start_time):
        self.start_time = start_time

    @property
    def _frequency(self):
        return IntervalItem.Frequency.Daily

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    @property_is_valid_time
    @property_not_nullable
    def start_time(self, value):
        self._start_time = value


class WeeklyInterval(object):
    def __init__(self, start_time, *interval_values):
        self.start_time = start_time
        self.interval = interval_values

    @property
    def _frequency(self):
        return IntervalItem.Frequency.Weekly

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    @property_is_valid_time
    @property_not_nullable
    def start_time(self, value):
        self._start_time = value

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, interval_values):
        if not all(hasattr(IntervalItem.Day, day) for day in interval_values):
            raise ValueError("Invalid week day defined " + str(interval_values))

        self._interval = interval_values

    def _interval_type_pairs(self):
        return [(IntervalItem.Occurrence.WeekDay, day) for day in self.interval]


class MonthlyInterval(object):
    def __init__(self, start_time, interval_value):
        self.start_time = start_time
        self.interval = str(interval_value)

    @property
    def _frequency(self):
        return IntervalItem.Frequency.Monthly

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    @property_is_valid_time
    @property_not_nullable
    def start_time(self, value):
        self._start_time = value

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, interval_value):
        error = "Invalid interval value for a monthly frequency: {}.".format(interval_value)

        # interval_value can either be one of the strings below or the string
        # rep of numbers between 1 and 31

        try:
            is_valid = (
                interval_value in {
                    "LastDay", # I suppose "LastDay" was changed to "Last", but who knows?
                    "First",
                    "Second",
                    "Third",
                    "Fourth",
                    "Fifth",
                    "Last",
                } or (1 <= int(interval_value) <= 31)
            )
        except ValueError:
            raise ValueError(error)

        if not is_valid:
            raise ValueError(error)

        self._interval = str(interval_value)

    def _interval_type_pairs(self):
        return [(IntervalItem.Occurrence.MonthDay, self.interval)]
