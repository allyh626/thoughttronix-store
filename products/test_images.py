"""Product images: upload validation, cleanup, display, and the seed."""

import io
from http import HTTPStatus

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.templatetags.static import static
from django.urls import reverse
from PIL import Image

from .models import Product
from .test_backoffice import product_data
from .validators import MAX_IMAGE_SIZE

pytestmark = pytest.mark.django_db

BANNER = (
    "Your image was rejected, so nothing was saved. "
    "Fix the problem below and choose the file again."
)


def image_upload(name, image_format="PNG"):
    """A small, noisy image (so it compresses to more than a header)."""
    buffer = io.BytesIO()
    Image.effect_noise((64, 64), 50).save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue())


def truncated_upload(name):
    whole = image_upload(name).read()
    return SimpleUploadedFile(name, whole[: len(whole) // 2])


def create_url():
    return reverse("products:manage_product_create")


def update_url(product):
    return reverse("products:manage_product_update", kwargs={"pk": product.pk})


def edit_data(product, **overrides):
    """The product's current values as edit-form POST data."""
    data = product_data(product.category, name=product.name, slug=product.slug)
    data.update(overrides)
    return data


# --- Upload validation -------------------------------------------------------


@pytest.mark.parametrize(
    ("upload", "message"),
    [
        (
            SimpleUploadedFile("notes.txt", b"Remember to buy milk."),
            '"notes.txt" isn\'t an image file. Please upload a JPEG, PNG, '
            "or WebP image.",
        ),
        (
            image_upload("spin.gif", "GIF"),
            '"spin.gif" is a GIF image, which we can\'t display on the store. '
            "Please save it as a JPEG, PNG, or WebP and upload it again.",
        ),
        (
            image_upload("scan.tiff", "TIFF"),
            '"scan.tiff" is a TIFF image, which we can\'t display on the store. '
            "Please save it as a JPEG, PNG, or WebP and upload it again.",
        ),
        (
            SimpleUploadedFile(
                "IMG_0042.HEIC", b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic"
            ),
            '"IMG_0042.HEIC" is a HEIC (iPhone) image, which we can\'t display '
            "on the store. Please save it as a JPEG, PNG, or WebP and upload it "
            "again.",
        ),
        (
            SimpleUploadedFile("huge.png", b"\0" * (MAX_IMAGE_SIZE + 1)),
            '"huge.png" is 5.1 MB. The largest image we can accept is 5 MB. '
            "Please choose a smaller file.",
        ),
        (
            truncated_upload("half.png"),
            '"half.png" is damaged or incomplete, so it can\'t be shown. Try '
            "saving or exporting the image again, then upload the new copy.",
        ),
        (
            SimpleUploadedFile("blank.png", b""),
            '"blank.png" is empty. Please choose the image file again.',
        ),
    ],
    ids=["not-an-image", "gif", "tiff", "heic", "too-large", "damaged", "empty"],
)
def test_rejected_upload_shows_message_and_banner(
    client, staff_user, category, media_root, upload, message
):
    client.force_login(staff_user)

    response = client.post(create_url(), product_data(category, image=upload))

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["image"] == [message]
    assert BANNER in response.content.decode()
    assert not Product.objects.exists()
    assert not media_root.exists() or not any(media_root.rglob("*.*"))


def test_no_banner_when_only_other_fields_fail(client, staff_user, category):
    client.force_login(staff_user)

    response = client.post(create_url(), product_data(category, name=""))

    assert response.status_code == HTTPStatus.OK
    assert BANNER not in response.content.decode()


def test_upload_is_saved_as_slug_with_detected_extension(
    client, staff_user, category, media_root
):
    """A JPEG sent as .png is saved as <slug>.jpg."""
    client.force_login(staff_user)

    response = client.post(
        create_url(),
        product_data(category, image=image_upload("photo.png", "JPEG")),
    )

    assert response.status_code == HTTPStatus.FOUND
    product = Product.objects.get()
    assert product.image.name == "products/mindsync-sleep-halo.jpg"
    assert (media_root / product.image.name).exists()


@pytest.mark.parametrize("image_format", ["PNG", "WEBP"])
def test_png_and_webp_are_accepted(
    client, staff_user, category, media_root, image_format
):
    client.force_login(staff_user)

    client.post(
        create_url(),
        product_data(category, image=image_upload("photo", image_format)),
    )

    extension = image_format.lower()
    assert (
        Product.objects.get().image.name == f"products/mindsync-sleep-halo.{extension}"
    )


def test_remove_ticked_with_new_file_is_rejected(
    client, staff_user, product_with_image
):
    client.force_login(staff_user)

    response = client.post(
        update_url(product_with_image),
        edit_data(
            product_with_image, image=image_upload("new.png"), **{"image-clear": "on"}
        ),
    )

    assert response.context["form"].errors["image"] == [
        'Please either choose a new image or tick "Remove current image," not both.'
    ]
    assert BANNER in response.content.decode()


def test_edit_form_shows_preview_and_remove_checkbox(
    client, staff_user, product_with_image
):
    client.force_login(staff_user)

    page = client.get(update_url(product_with_image)).content.decode()

    assert 'enctype="multipart/form-data"' in page
    assert product_with_image.image.url in page
    assert 'name="image-clear"' in page
    assert "Remove current image" in page
    assert "JPEG, PNG, or WebP image, up to 5 MB." in page


def test_new_product_form_has_no_remove_checkbox(client, staff_user):
    client.force_login(staff_user)

    page = client.get(create_url()).content.decode()

    assert 'name="image-clear"' not in page


# --- Cleanup -----------------------------------------------------------------


def test_remove_checkbox_clears_image_and_deletes_file_after_commit(
    client,
    staff_user,
    product_with_image,
    media_root,
    django_capture_on_commit_callbacks,
):
    client.force_login(staff_user)
    old_file = media_root / product_with_image.image.name

    with django_capture_on_commit_callbacks() as callbacks:
        client.post(
            update_url(product_with_image),
            edit_data(product_with_image, **{"image-clear": "on"}),
        )
        assert old_file.exists()  # not before the commit
    for callback in callbacks:
        callback()

    product_with_image.refresh_from_db()
    assert not product_with_image.image
    assert not old_file.exists()


def test_replacing_image_deletes_old_file_after_commit(
    client,
    staff_user,
    product_with_image,
    media_root,
    django_capture_on_commit_callbacks,
):
    client.force_login(staff_user)
    old_file = media_root / product_with_image.image.name

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            update_url(product_with_image),
            edit_data(product_with_image, image=image_upload("new.png")),
        )

    product_with_image.refresh_from_db()
    assert product_with_image.image.name != "products/seraphine-home-hub.png"
    assert (media_root / product_with_image.image.name).exists()
    assert not old_file.exists()


def test_saving_without_new_image_keeps_file(
    client,
    staff_user,
    product_with_image,
    media_root,
    django_capture_on_commit_callbacks,
):
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            update_url(product_with_image),
            edit_data(product_with_image, tagline="New tagline"),
        )

    product_with_image.refresh_from_db()
    assert product_with_image.image.name == "products/seraphine-home-hub.png"
    assert (media_root / product_with_image.image.name).exists()


def test_deleting_product_deletes_file_after_commit(
    client,
    staff_user,
    product_with_image,
    media_root,
    django_capture_on_commit_callbacks,
):
    client.force_login(staff_user)
    old_file = media_root / product_with_image.image.name

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse(
                "products:manage_product_delete", kwargs={"pk": product_with_image.pk}
            )
        )

    assert not Product.objects.exists()
    assert not old_file.exists()


# --- Display -----------------------------------------------------------------


def test_display_image_url_is_the_upload(product_with_image):
    assert product_with_image.display_image_url == product_with_image.image.url


def test_display_image_url_falls_back_without_image(product):
    assert product.display_image_url == static(
        "images/placeholders/home-assistants.svg"
    )


def test_display_image_url_falls_back_when_file_is_missing(
    product_with_image, media_root
):
    (media_root / product_with_image.image.name).unlink()

    assert product_with_image.display_image_url == static(
        "images/placeholders/home-assistants.svg"
    )


def test_catalog_and_detail_show_the_upload(client, product_with_image):
    url = product_with_image.image.url

    assert url in client.get(reverse("products:catalog")).content.decode()
    assert url in client.get(product_with_image.get_absolute_url()).content.decode()


# --- The seed ----------------------------------------------------------------


def test_seed_attaches_the_twelve_images(media_root):
    call_command("seed")
    call_command("seed")

    with_images = Product.objects.exclude(image="")
    assert with_images.count() == 12
    assert set(with_images.values_list("image", flat=True)) == {
        f"products/{slug}.png"
        for slug in [
            "calm-collar",
            "crowdcalm-array",
            "dreamweaver",
            "hush",
            "mindsync",
            "mindsync-duo",
            "moodset",
            "recallpro",
            "seraphine",
            "soulsear-mark-ii",
            "syncrest",
            "veil",
        ]
    }
    assert len(list((media_root / "products").iterdir())) == 12


def test_seed_rejects_a_bad_image(media_root, tmp_path, monkeypatch):
    seed_images = tmp_path / "seed_images"
    seed_images.mkdir()
    (seed_images / "seraphine.png").write_bytes(b"not really a png")
    monkeypatch.setattr(
        "products.management.commands.seed.SEED_IMAGES_DIR", seed_images
    )

    with pytest.raises(CommandError, match="seraphine.png") as error:
        call_command("seed")

    assert "isn't an image file" in str(error.value)
    assert not Product.objects.exists()  # rolled back
