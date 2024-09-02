import os.path
from datetime import datetime
from fpdf import FPDF
from timetable import get_attendance_count


class PDF(FPDF):

    def __init__(self, month, daycare, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.month = month
        self.daycare = daycare


    def header(self):
        self.image(f'{self.daycare.logo}', 0, 0, self.w, self.h)

        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f'{self.daycare.name} Invoice', 0, 1, 'C')

        self.set_font('Arial', '', 10)
        height = 5
        self.cell(0, height, f'{self.daycare.name}', 0, 1, 'R')
        self.cell(0, height, f'{self.daycare.address}', 0, 1, 'R')
        self.cell(0, height, f'{self.daycare.town_state_zip}', 0, 1, 'R')
        self.cell(0, height, f'Phone: f{self.daycare.phone}', 0, 1, 'R')
        self.cell(0, height, f'EIN: f{self.daycare.ein}', 0, 1, 'R')
        self.ln(10)  # Add a line break

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def save_pdf(invoice, daycare, directory=None):
    pdf = PDF(invoice.month, daycare)
    pdf.add_page()

    parent = invoice.parent

    # Title
    pdf.ln(30)  # Add a line break


    pdf.chapter_title(f'Parent: {parent.name}')
    pdf.cell(0, 5, f'Invoice Period: {invoice.month}/{invoice.year}', 0, 1)
    pdf.cell(0, 5, f'Generate on: {invoice.gen_date}', 0, 1)

    pdf.ln()

    # Table header
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(30, 10, 'Child', 1,0, 'C')
    pdf.cell(50, 10, 'Days', 1)
    pdf.cell(30, 10, 'Days Count', 1)
    pdf.cell(30, 10, 'Rate', 1)
    pdf.cell(30, 10, 'Fee', 1)
    pdf.ln()

    # Table body
    pdf.set_font('Arial', '', 12)
    for child in parent.children:
        pdf.cell(30, 10, str(child.name), 1)
        pdf.set_font('Arial', '', 8)
        pdf.cell(50, 10, str(",".join(Invoice._make_date_range(child.current_attendance_dates))), 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(30, 10, str(len(child.current_attendance_dates)), 1)
        pdf.cell(30, 10, f'${str(child.day_rate)}', 1)
        pdf.cell(30, 10, f'${str(child.current_fee)}', 1)
        pdf.ln()

    pdf.set_font('Arial', 'B', 12)
    pdf.ln(10)
    pdf.cell(0, 10, f'Total: ${invoice.fee}', 0, 1, 'R')

    # Save PDF
    pdf_output_filename = f'invoice_{parent.name}_{invoice.month}-{invoice.year}.pdf'
    if directory is not  None:
        pdf_output_filename = os.path.join(directory, pdf_output_filename)
    pdf.output(pdf_output_filename)

class Invoice(object):
    def __init__(self, year, month, parent, public_holidays):
        self.year = year
        self.month = month
        self.parent = parent
        self.public_holidays = public_holidays

        self.fee = 0
        self.days_count = 0
        self.gen_date = datetime.now().strftime("%m-%d-%Y")

    @staticmethod
    def generate_invoice(year, month, parent, public_holidays):
        days_count = 0
        fee = 0
        for child in parent.children:
            days = get_attendance_count(year, month, child.child_schedule, public_holidays)
            # print(f"Child {child.name} attended {days} days")
            # print(f"Child {child.name} attended {','.join(Invoice._make_date_range(days))}")
            child.current_attendance_dates = days
            child.current_fee = len(days) * child.day_rate
            fee += child.current_fee
            days_count += len(days)
        invoice = Invoice(year, month, parent, public_holidays)
        invoice.fee = fee
        invoice.days_count = days_count
        return invoice

    @staticmethod
    def _append_range(start, end, date_range):
        if start == end:
            date_range.append(f'{start}')
        else:
            date_range.append(f'{start}-{end}')

    @staticmethod
    def _make_date_range(days):
        if len(days) == 0:
            return []

        days = [int(day_str) for day_str in days]

        date_range = []
        start = end = days[0]

        for day in days[1:]:
            if day - end == 1:
                end = day
            else:
                Invoice._append_range(start, end, date_range)
                start = end = day
        Invoice._append_range(start, end, date_range)

        return date_range

