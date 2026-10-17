"""The development email backend: links print whole, ready to paste."""

import io
import re

from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.urls import reverse

from config.email_backends import ReadableConsoleEmailBackend

LONG_LINK = "http://127.0.0.1:8000/accounts/verify-email/" + "a1B2c3" * 15 + "/"


def test_long_lines_print_whole_and_unencoded():
    stream = io.StringIO()
    message = EmailMessage(
        "Confirm your ThoughtTronix email",
        f"Hi — open this link:\n\n{LONG_LINK}\n",
        "no-reply@thoughttronix.example",
        ["casey@example.com"],
    )

    ReadableConsoleEmailBackend(stream=stream).send_messages([message])

    output = stream.getvalue()
    assert LONG_LINK in output.splitlines()
    assert "Hi — open this link:" in output
    assert "quoted-printable" not in output
    assert "From: no-reply@thoughttronix.example" in output
    assert "To: casey@example.com" in output
    assert "Subject: Confirm your ThoughtTronix email" in output


def test_a_link_copied_from_the_terminal_verifies_the_email(
    client, db, settings, capsys
):
    settings.EMAIL_BACKEND = "config.email_backends.ReadableConsoleEmailBackend"
    client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "fresh@example.com",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
    )

    printed = capsys.readouterr().out
    link = re.search(r"https?://\S+/accounts/verify-email/\S+", printed).group()
    client.get(link)

    assert get_user_model().objects.get(username="fresh-thinker").email_verified
