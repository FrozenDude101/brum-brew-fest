import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid
from typing import Any

from jinja2 import Environment, PackageLoader, Template, select_autoescape

from api.users.db import FastApiUser
from api.utils import (
    get_env_variable_force,
    get_env_variable_with_default,
    get_secret_force,
)

from_email = get_env_variable_force("FROM_EMAIL")
smtp_server = get_env_variable_force("SMTP_SERVER")
smtp_port = int(get_env_variable_force("SMTP_PORT"))
smtp_user = get_env_variable_force("SMTP_USER")
smtp_password = get_secret_force("SMTP_PASSWORD")

if get_env_variable_force("API_ENV") == "prod":
    client_protocol = get_env_variable_force("CLIENT_PROTOCOL")
    client_host = get_env_variable_force("CLIENT_HOST")
else:
    client_protocol = get_env_variable_with_default("CLIENT_PROTOCOL", "http")
    client_host = get_env_variable_with_default("CLIENT_HOST", "localhost")


def render_template(template: Template, args: dict[str, Any]) -> str:
    return template.render(args)  # type: ignore


def write_email_template(template_name: str, args: dict[str, Any]) -> str:
    env = Environment(
        loader=PackageLoader("api"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_name)
    email = render_template(template, args)
    return email


def write_email(subject: str, to_email: str, body: str) -> MIMEMultipart:
    message = MIMEMultipart("mixed")
    message["Subject"] = subject
    message["From"] = formataddr(("Brum Brew Fest Tracker", from_email))
    message["To"] = to_email
    message["Message-ID"] = make_msgid()
    message.attach(MIMEText(body))
    return message


def send_email(message: MIMEMultipart):
    conn = smtplib.SMTP(smtp_server, smtp_port)
    conn.starttls()
    conn.set_debuglevel(False)
    conn.login(smtp_user, smtp_password)
    try:
        conn.sendmail(from_email, message["To"], message.as_string())
    finally:
        conn.close()


def send_verify_email(user: FastApiUser, token: str) -> None:
    body = write_email_template(
        "verify.txt",
        {"verify_url": f"{client_protocol}://{client_host}/verify/{token}"},
    )
    message = write_email("[bbf] Verify your account", user.email, body)
    send_email(message)


def send_forgot_password_email(user: FastApiUser, token: str) -> None:
    body = write_email_template(
        "forgot-password.txt",
        {"reset_url": f"{client_protocol}://{client_host}/reset/{token}"},
    )
    message = write_email("[bbf] Password reset request", user.email, body)
    send_email(message)
