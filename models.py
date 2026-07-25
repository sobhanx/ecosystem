"""Data models for ecosystem services."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Service(models.Model):
    """
    External service belonging to the same product ecosystem.

    Administrators register sibling sites (academy, shop, blog, dashboard,
    and so on). Templates render them by free-form ``location`` key via the
    ``{% ecosystem %}`` inclusion tag.

    Location keys are arbitrary strings. Adding a new placement never requires
    code changes—only a new admin value and a matching template tag call.
    """

    name = models.CharField(
        _("name"),
        max_length=150,
        help_text=_(
            'Short label visitors and editors will recognize '
            '(for example "Academy" or "Shop").'
        ),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=150,
        unique=True,
        blank=True,
        help_text=_(
            "Internal unique ID. Leave blank to generate from the name; "
            "existing values are kept when the name changes."
        ),
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_(
            "Optional notes for your team. Not shown on the site by default."
        ),
    )
    logo = models.ImageField(
        _("logo"),
        upload_to="ecosystem/services/",
        blank=True,
        help_text=_(
            "Optional image shown next to the service name "
            "(stored under MEDIA_ROOT/ecosystem/services/)."
        ),
    )
    url = models.URLField(
        _("URL"),
        help_text=_(
            "Full web address, including https:// "
            "(for example https://academy.example.com)."
        ),
    )
    location = models.CharField(
        _("location"),
        max_length=100,
        help_text=_(
            "Placement key matched exactly by the template tag. "
            "Prefer choosing a known key in admin; new keys stay allowed "
            '(examples: "footer", "pricing_page").'
        ),
    )
    display_order = models.PositiveIntegerField(
        _("display order"),
        default=0,
        help_text=_(
            "Controls the order within the same placement. "
            "Smaller numbers appear first."
        ),
    )
    active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Uncheck to hide this service everywhere without deleting it."
        ),
    )
    open_in_new_tab = models.BooleanField(
        _("open in new tab"),
        default=True,
        help_text=_("When checked, the link opens in a new browser tab."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")
        ordering = ("display_order", "name")
        indexes = [
            # Admin list_filter / lookups by placement key alone.
            models.Index(fields=["location"], name="ecosystem_svc_location_idx"),
            # Hot path: active services for a location, already sorted.
            models.Index(
                fields=["active", "location", "display_order", "name"],
                name="ecosystem_svc_lookup_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(location=""),
                name="ecosystem_svc_location_not_empty",
            ),
            models.CheckConstraint(
                condition=~Q(slug=""),
                name="ecosystem_svc_slug_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Normalize fields and generate a slug when the field is empty."""
        self.location = self.location.strip()
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def _build_unique_slug(self) -> str:
        """Build a unique slug from ``name`` using Django's ``slugify``."""
        base_slug = slugify(self.name) or "service"
        candidate = base_slug
        suffix = 2
        queryset = type(self)._default_manager.all()
        if self.pk is not None:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        return candidate
