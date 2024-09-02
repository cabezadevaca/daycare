from datetime import datetime, timedelta


class PublicHolidays:
    def __init__(self, holidays):
        """
        Initialize the PublicHolidays instance.

        :param holidays: List of public holidays in (YYYY-MM-DD) format.
        """
        self.holidays = holidays
        self.holidays_set = set(holidays)  # For faster lookup

    def get_holidays_in_month(self, year, month):
        """
        Get public holidays in a specific month for a specific year.

        :param year: Year of interest (e.g., 2024)
        :param month: Month of interest (1 to 12)
        :return: Set of public holidays in (YYYY-MM-DD) format for the given month and year
        """
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        month_holidays = set()
        for holiday in self.holidays:
            holiday_date = datetime.strptime(holiday, "%Y-%m-%d").date()
            if start_date.date() <= holiday_date <= end_date.date():
                month_holidays.add(holiday)

        return month_holidays


def get_attendance_count(year, month, person_schedule, public_holidays_instance):
    """
    Calculate the number of days a person attends in a given month.

    :param year: Year of interest (e.g., 2024)
    :param month: Month of interest (1 to 12)
    :param person_schedule: List of weekdays the person attends (0=Monday, 1=Tuesday, ..., 6=Sunday)
    :param public_holidays_instance: An instance of PublicHolidays class
    :return: Number of days attended
    """

    # Define the first and last day of the month
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    # Get public holidays for the month
    public_holidays = public_holidays_instance.get_holidays_in_month(year, month)

    # Initialize attendance count
    attendance_count = 0
    attendance_days = []

    # Iterate through each day of the month
    current_day = first_day
    while current_day <= last_day:
        # Check if the current day is a public holiday
        if current_day.date().isoformat() not in public_holidays:
            # Check if the current day is one of the person's scheduled days
            if current_day.weekday() in person_schedule:
                attendance_count += 1
                week_day = current_day.date().strftime('%d')
                attendance_days.append(week_day)

        # Move to the next day
        current_day += timedelta(days=1)

    return attendance_days


# # Example usage
# year = 2024
# month = 8  # August
# person_schedule = [0, 1, 2, 3, 4]  # Attends from Monday to Friday
# holidays = ["2024-08-15", "2024-08-25", "2024-08-01"]  # Example public holidays
#
# # Create an instance of PublicHolidays
# public_holidays_instance = PublicHolidays(holidays)
#
# # Calculate the number of days attended
# days_attended = get_attendance_count(year, month, person_schedule, public_holidays_instance)
# print(f"Number of days attended: {days_attended}")