"""Email backends for local development."""

from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend


class ReadableConsoleEmailBackend(ConsoleEmailBackend):
    """Prints each email's plain text to the terminal, ready to copy.

    Django's own console backend prints the encoded message, as it would
    travel over the wire. Lines over 78 characters — like a verification
    link — come out quoted-printable, wrapped with a trailing ``=``, so a
    pasted link is broken. This prints the body exactly as written instead.
    """

    def write_message(self, message):
        self.stream.write(f"From: {message.from_email}\n")
        self.stream.write(f"To: {', '.join(message.to)}\n")
        self.stream.write(f"Subject: {message.subject}\n\n")
        self.stream.write(f"{message.body}\n")
        self.stream.write("-" * 79)
        self.stream.write("\n")
