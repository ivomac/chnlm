import smtplib
import ssl
from email.mime.text import MIMEText
from os import environ as env

context = ssl.create_default_context()


def send_email_notification(subject, message):
    password = env["EMAIL_PWD"]
    if password:
        host = "mail.epfl.ch"
        port = 25
    else:
        host = "localhost"
        port = 1025

    with smtplib.SMTP(host, port) as smtp:
        if password:
            smtp.starttls(context=context)
            smtp.login("bbp.channelpedia", password)

        msg = MIMEText(message, "html")
        msg["From"] = "bbp.channelpedia@epfl.ch"
        msg["Subject"] = subject
        msg["To"] = env["EMAIL_ADDRESS"]

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        smtp.sendmail(msg["From"], [msg["To"]], msg.as_string())
