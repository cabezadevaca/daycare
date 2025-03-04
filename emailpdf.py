"""
ChatGPT version, modified
"""
import os.path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText


def send_email_with_pdf(sender_email, sender_password, receiver_email, subject, body, pdf_file_path):
    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Attach the body with the msg instance
    msg.attach(MIMEText(body, 'plain'))

    # Open the PDF file in binary mode
    with open(pdf_file_path, 'rb') as attachment:
        # Create a MIMEBase object
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())

        # Encode the payload using base64
        encoders.encode_base64(part)

        # Add header to the attachment
        fname = os.path.basename(pdf_file_path)
        part.add_header('Content-Disposition', f'attachment; filename={fname}')

        # Attach the PDF file to the email
        msg.attach(part)

    # Set up the server and send the email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        print('Server onnected')
        server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.login(sender_email, sender_password)  # Log in to your email account
        server.send_message(msg)  # Send the email
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()  # Close the server connection


# Usage
sender_email = 'regina.rafikova@gmail.com'
sender_password = 'cbkl kwkz sfzx yued'
receiver_email = 'rrv2005@gmail.com'
subject = 'Invoice Test'
body = 'This is the body of the email.'
pdf_file_path = 'C:\\Users\\regina\\Desktop\\RKG\\invoices\\2024-10\\test.pdf'

# send_email_with_pdf(sender_email, sender_password, receiver_email, subject, body, pdf_file_path)
