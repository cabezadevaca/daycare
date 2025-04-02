import json
import os
from datetime import datetime

import pandas as pd

import emailpdf
from actors import DayCare, Family, Parent, Child
from invoice import Invoice, save_pdf, save_family_pdf
from timetable import  PublicHolidays

public_holidays = PublicHolidays(
    [
        "2024-09-02",
        "2024-11-28",
        "2024-11-29",
        "2024-12-25",
        # NY Eve
        "2024-12-30",
        "2024-12-31",
        # NY
        "2025-01-01",

        # Feb school vacation
        "2025-02-17",
        "2025-02-18",
        "2025-02-19",
        "2025-02-20",
        "2025-02-21"
    ])

motd = ""

# Function to load the family data from a configuration file
def load_families_from_config(config_file):
    with open(config_file, 'r') as f:
        config_data = json.load(f)

    families = []

    fam_id = 0
    parent_id = 0
    child_id = 0
    # Create families
    for family_data in config_data.get('families', []):
        family = Family(fam_id)
        fam_id += 1

        # Create parents and assign them to the family
        for parent_data in family_data.get('parents', []):
            parent = Parent(id=parent_id, name=parent_data['name'], email=parent_data['email'])
            family.add_parent(parent)
            parent_id += 1

        # Create kids and assign them to the family
        for kid_data in family_data.get('kids', []):
            child = Child(id=child_id, name=kid_data['name'], dob=kid_data['dob'], child_schedule=kid_data['attendance'],
                          day_rate=kid_data['fee'], parent=None)
            family.add_child(child)
            child_id += 1

        families.append(family)

    return families

def create_dirs(year, month, path):
    if not os.path.exists(path):
        os.mkdir(path)
    path = os.path.join(path, f'{month}-{year}')
    if not os.path.exists(path):
        os.mkdir(path)
    return  path

def month_to_str(year, month):
    return datetime(year, month, 1).strftime("%B")

def  family_invoice(year, month, family, path, debug=False):
    invoice = Invoice.generate_family_invoice(year, month, family, public_holidays)

    fname = save_family_pdf(invoice, daycare, path)
    print(f'Saving PDF to: {os.path.basename(fname)}')

    passwd = emailpdf.sender_password
    month_str = month_to_str(year, month)

    for parent in family.parents:
        if debug:
            parent.email = "rrv2005@gmail.com"
        first, *last = parent.name.split()

        emailpdf.send_email_with_pdf(emailpdf.sender_email, passwd,
                                 parent.email, f'IClever Invoice for {month_str} {year}',
                                 f'Dear {first}, sending you the {month_str} {year} invoice. '
                                 f'\n{motd}'
                                 f'\n\nThanks\nRegina',
                                 fname
                                 )


    return  invoice

year = 2025
month = 4
fee = 0
_path = "../invoices"

if __name__ == "__main__":

    daycare = DayCare.load_config("daycare.json")
    fams = load_families_from_config('families.json')

    _path = create_dirs(year, month, _path)

    df = pd.DataFrame()
    for family in fams:
        print(family.children)
        invoice = family_invoice(year, month, family, _path, debug=True)
        df = invoice.add_to_df(df)
        print(f'Fam fee:{invoice.fee}')
        fee += invoice.fee

    df.to_csv(os.path.join(_path, 'summary.csv'))
    print(f'Fee: {fee}')