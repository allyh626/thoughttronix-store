"""What a valid product image is — the one source of truth.

The back-office upload field (``products.forms.ProductImageField``) and
the ``seed`` command share this validator, so a seeded image could also
have been uploaded, and vice versa. Formats are judged by what Pillow
detects in the file, never by the filename's extension.
"""

import math
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

# Pillow format name -> the extension the file is saved under. Phone
# cameras often write JPEGs that Pillow reports as MPO (a JPEG with
# extra frames); browsers show them as plain JPEGs.
IMAGE_EXTENSIONS = {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp"}

IMAGE_HELP_TEXT = "JPEG, PNG, or WebP image, up to 5 MB."

# HEIC, the iPhone's default photo format, starts with an ISO "ftyp" box
# naming one of these brands. Pillow can't open HEIC, so it's recognized
# by that header alone, to tell the employee what they actually have.
HEIC_BRANDS = {
    b"heic",
    b"heix",
    b"heim",
    b"heis",
    b"hevc",
    b"hevx",
    b"hevm",
    b"hevs",
    b"mif1",
    b"msf1",
}


def _is_heic(file) -> bool:
    file.seek(0)
    header = file.read(12)
    return header[4:8] == b"ftyp" and header[8:12] in HEIC_BRANDS


def _unsupported_format(name, format_name) -> ValidationError:
    return ValidationError(
        f'"{name}" is a {format_name} image, which we can\'t display on the '
        f"store. Please save it as a JPEG, PNG, or WebP and upload it again.",
        code="unsupported_format",
    )


def validate_product_image(file) -> str:
    """Accept a JPEG, PNG, or WebP image of at most 5 MB, fully decodable.

    ``file`` is any Django ``File`` (an upload, or a file opened from
    disk). Returns the extension the image should be saved under, judged
    from its detected format. Raises ``ValidationError`` with the
    employee-facing message otherwise. Leaves the file at position 0.
    """
    name = Path(file.name).name

    if not file.size:
        raise ValidationError(
            f'"{name}" is empty. Please choose the image file again.',
            code="empty",
        )
    if file.size > MAX_IMAGE_SIZE:
        # Round up, so a file just over the limit never reads as "5.0 MB".
        megabytes = math.ceil(file.size / (1024 * 1024) * 10) / 10
        raise ValidationError(
            f'"{name}" is {megabytes:.1f} MB. The largest image we can accept '
            f"is 5 MB. Please choose a smaller file.",
            code="too_large",
        )

    damaged = ValidationError(
        f'"{name}" is damaged or incomplete, so it can\'t be shown. Try saving '
        f"or exporting the image again, then upload the new copy.",
        code="damaged",
    )

    file.seek(0)
    try:
        try:
            image = Image.open(file)
        except UnidentifiedImageError:
            if _is_heic(file):
                raise _unsupported_format(name, "HEIC (iPhone)") from None
            raise ValidationError(
                f'"{name}" isn\'t an image file. Please upload a JPEG, PNG, '
                f"or WebP image.",
                code="not_an_image",
            ) from None
        except Exception:
            raise damaged from None

        if image.format not in IMAGE_EXTENSIONS:
            raise _unsupported_format(name, image.format)

        # verify() only reads the header; load() decodes every pixel, so a
        # truncated or corrupt file fails here rather than on the store.
        try:
            image.load()
        except Exception:
            raise damaged from None
        return IMAGE_EXTENSIONS[image.format]
    finally:
        file.seek(0)
