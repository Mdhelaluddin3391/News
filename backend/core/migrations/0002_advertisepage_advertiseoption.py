# Generated manually on 2026-03-30

from django.db import migrations, models


def seed_advertise_defaults(apps, schema_editor):
    AdvertisePage = apps.get_model("core", "AdvertisePage")
    AdvertiseOption = apps.get_model("core", "AdvertiseOption")

    if not AdvertisePage.objects.exists():
        AdvertisePage.objects.create()

    if AdvertiseOption.objects.exists():
        return

    AdvertiseOption.objects.bulk_create(
        [
            AdvertiseOption(
                title="Header Banner",
                description=(
                    "Premium visibility at the very top of our website. Appears on all "
                    "pages. Highly recommended for maximum reach."
                ),
                icon_class="fas fa-rectangle-ad",
                inquiry_value="Header Banner",
                sort_order=1,
                show_on_page=True,
                show_in_inquiry_form=True,
            ),
            AdvertiseOption(
                title="Sidebar Top",
                description=(
                    "Sticky advertisement on the right sidebar. Stays visible as users "
                    "scroll through breaking news and articles."
                ),
                icon_class="fas fa-border-all",
                inquiry_value="Sidebar Ad",
                sort_order=2,
                show_on_page=True,
                show_in_inquiry_form=True,
            ),
            AdvertiseOption(
                title="In-Article Ad",
                description=(
                    "Placed directly inside our news articles. Great for capturing the "
                    "attention of highly engaged readers."
                ),
                icon_class="fas fa-newspaper",
                inquiry_value="In-Article Ad",
                sort_order=3,
                show_on_page=True,
                show_in_inquiry_form=True,
            ),
            AdvertiseOption(
                title="Brand Collaboration",
                description=(
                    "Sponsored posts, brand campaigns, and custom integrations tailored "
                    "to your launch timeline and audience goals."
                ),
                icon_class="fas fa-handshake",
                inquiry_value="Brand Collaboration / Sponsored Post",
                sort_order=4,
                show_on_page=False,
                show_in_inquiry_form=True,
            ),
            AdvertiseOption(
                title="Consultation",
                description="Need help selecting a package? Our team can suggest the right placement mix.",
                icon_class="fas fa-comments",
                inquiry_value="Not sure yet, need consultation",
                sort_order=5,
                show_on_page=False,
                show_in_inquiry_form=True,
            ),
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdvertisePage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hero_title", models.CharField(default="Grow Your Brand With Forex Times", max_length=200)),
                (
                    "hero_description",
                    models.TextField(
                        default=(
                            "Reach a highly engaged audience through our premium digital news "
                            "platform. We offer strategic ad placements to maximize your visibility."
                        )
                    ),
                ),
                ("slots_section_title", models.CharField(default="Available Ad Slots", max_length=200)),
                ("inquiry_title", models.CharField(default="Advertisement Inquiry", max_length=200)),
                (
                    "inquiry_description",
                    models.TextField(
                        default=(
                            "Fill out the form below and our advertising team will get back to you "
                            "with pricing and analytics details."
                        )
                    ),
                ),
                ("submit_button_text", models.CharField(default="Submit Inquiry", max_length=80)),
                (
                    "success_message",
                    models.CharField(
                        default="Thank you for your interest! Our advertising team will contact you shortly.",
                        max_length=255,
                    ),
                ),
            ],
            options={
                "verbose_name": "Advertise Page",
                "verbose_name_plural": "Advertise Page",
            },
        ),
        migrations.CreateModel(
            name="AdvertiseOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("description", models.TextField()),
                (
                    "icon_class",
                    models.CharField(
                        default="fas fa-bullhorn",
                        help_text="Font Awesome class, e.g. fas fa-rectangle-ad",
                        max_length=100,
                    ),
                ),
                (
                    "inquiry_value",
                    models.CharField(
                        help_text="Dropdown me yahi option value use hogi.",
                        max_length=150,
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "show_on_page",
                    models.BooleanField(
                        default=True,
                        help_text="Enable ho to advertise page ke cards me dikhega.",
                    ),
                ),
                (
                    "show_in_inquiry_form",
                    models.BooleanField(
                        default=True,
                        help_text="Enable ho to inquiry dropdown me dikhega.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Advertise Option",
                "verbose_name_plural": "Advertise Options",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.RunPython(seed_advertise_defaults, migrations.RunPython.noop),
    ]
