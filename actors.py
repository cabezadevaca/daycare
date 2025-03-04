import json

from emailpdf import sender_password


class Family:

    def __init__(self, id):
        self.id = id
        self.parents = []
        self.children = []

    def add_parent(self, parent):
        self.parents.append(parent)

    def add_child(self, child):
        self.children.append(child)

class Person:
    def __init__(self, id, name):
        self.name = name
        self.id = id

    def __repr__(self):
        return self.name


class Child(Person):
    def __init__(self, id, name, dob, child_schedule, day_rate, parent):
        super().__init__(id, name)
        self.dob = dob
        self.child_schedule = child_schedule
        self.day_rate = day_rate
        self.parent = parent

        if parent is not None:
            self.parent.add_child(self)

        # accounting - current will be calculated in get_attendance_count for
        # a given month
        self.current_month = None
        self.current_fee = 0
        self.current_attendance_dates = []

    def __repr__(self):
        return f"Child(id={self.id}, name={self.name})"


class Parent(Person):
    def __init__(self, id, name, email):
        super().__init__(id, name)
        self.children = []
        self.email = email

    def add_child(self, child):
        self.children.append(child)


class DayCare:
    def __init__(self, name, town_state_zip, address, phone, ein, logo,
                 email, sender_through, sender_email, sender_password, invoice_prefix):
        self.name = name
        self.address = address
        self.town_state_zip = town_state_zip
        self.phone = phone
        self.ein = ein
        self.logo = logo
        self.email = email
        self.sender_through = sender_through
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.invoice_prefix = invoice_prefix
        self.children = []
        self._parents = set()
        self.families = set()


    @staticmethod
    def load_config(file_json):
        with open(file_json, 'r') as f:
            config_data = json.load(f)
            return DayCare(config_data['name'], config_data['zip'], config_data['address'],
                           config_data['phone'], config_data['ein'], config_data['letterhead'],
                           config_data['email'], config_data['sender_through'], config_data['sender_email'],
                           config_data['sender_password'], config_data['invoice_prefix'])


    def add_child(self, child):
        self.children.append(child)
        self.parents.add(child.parent)

    @property
    def parents(self) -> set:
        return self._parents

    def add_family(self, family):
        self.families.add(family)


