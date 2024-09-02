class Person:
    def __init__(self, id, name):
        self.name = name
        self.id = id


class Child(Person):
    def __init__(self, id, name, dob, child_schedule, day_rate, parent):
        super().__init__(id, name)
        self.dob = dob
        self.child_schedule = child_schedule
        self.day_rate = day_rate
        self.parent = parent
        self.parent.add_child(self)

        # accounting - current will be calculated in get_attendance_count for
        # a given month
        self.current_month = None
        self.current_fee = 0
        self.current_attendance_dates = []


class Parent(Person):
    def __init__(self, id, name, email):
        super().__init__(id, name)
        self.children = []
        self.email = email

    def add_child(self, child):
        self.children.append(child)


class DayCare:
    def __init__(self, name, town_state_zip, address, phone, ein, logo):
        self.name = name
        self.address = address
        self.town_state_zip = town_state_zip
        self.phone = phone
        self.ein = ein
        self.logo = logo
        self.children = []
        self._parents = set()

    def add_child(self, child):
        self.children.append(child)
        self.parents.add(child.parent)

    @property
    def parents(self) -> set:
        return self._parents


