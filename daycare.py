import os
from datetime import datetime

import pandas as pd

import emailpdf
from actors import DayCare, Family, Parent, Child
from database import init_db, DayCareDB, FamilyDB, PublicHolidayDB
from invoice import Invoice, save_pdf, save_family_pdf
from timetable import PublicHolidays

motd = ""


def load_public_holidays_from_db(session):
    """Load public holidays from the database and return a PublicHolidays instance."""
    rows = session.query(PublicHolidayDB).all()
    date_strings = [row.date.strftime("%Y-%m-%d") for row in rows]
    return PublicHolidays(date_strings)


def load_families_from_db(session):
    """Load all families (with parents and children) from the database."""
    return session.query(FamilyDB).all()

def create_dirs(year, month, path):
    if not os.path.exists(path):
        os.mkdir(path)
    path = os.path.join(path, f'{month}-{year}')
    if not os.path.exists(path):
        os.mkdir(path)
    return  path

def month_to_str(year, month):
    return datetime(year, month, 1).strftime("%B")

def  family_invoice(year, month, family, path, debug_email, public_holidays, daycare):
    invoice = Invoice.generate_family_invoice(year, month, family, public_holidays)

    fname = save_family_pdf(invoice, daycare, path)
    print(f'Saving PDF to: {os.path.basename(fname)}')

    passwd = daycare.sender_password
    month_str = month_to_str(year, month)

    for parent in family.parents:
        if debug_email is not None:
            parent.email = debug_email
        first, *last = parent.name.split()


        emailpdf.send_email_with_pdf(daycare.sender_email, passwd,
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

    engine, session = init_db()
    daycare = DayCareDB.load_from_db(session)
    fams = load_families_from_db(session)
    public_holidays = load_public_holidays_from_db(session)

    _path = create_dirs(year, month, _path)

    df = pd.DataFrame()
    for family in fams:
        print(family.children)
        debug_email = daycare.email
        invoice = family_invoice(year, month, family, _path, debug_email, public_holidays, daycare)
        invoice.save_to_db(session)
        df = invoice.add_to_df(df)
        print(f'Fam fee:{invoice.fee}')
        fee += invoice.fee

    session.commit()
    df.to_csv(os.path.join(_path, 'summary.csv'))
    print(f'Fee: {fee}')