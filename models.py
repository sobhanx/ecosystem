"""Data models for ecosystem locations and services."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Location(models.Model):
    """
    Named placement for ecosystem services (for example Footer or Header).

    ``key`` is the stable identifier used by ``{% ecosystem "key" %}``.
    """

    key = models.CharField(
        _("key"),
        max_length=100,
        unique=True,
        help_text=_(
            'Stable template-tag identifier (for example "footer" or '
            '"pricing_page"). Prefer leaving this unchanged after creation.'
        ),
    )
    name = models.CharField(
        _("name"),
        max_length=150,
        help_text=_(
            'Human-readable label shown in admin (for example "Footer").'
        ),
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Optional notes for editors about this placement."),
    )
    active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Uncheck to hide every service in this placement without "
            "deleting them."
        ),
    )
    position = models.PositiveIntegerField(
        _("position"),
        default=0,
        help_text=_("Order of this location in admin lists. Lower comes first."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("location")
        verbose_name_plural = _("locations")
        ordering = ("position", "name")
        constraints = [
            models.CheckConstraint(
                condition=~Q(key=""),
                name="ecosystem_location_key_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Normalize the location key before saving."""
        self.key = self.key.strip()
        if not self.name.strip():
            self.name = self.key
        else:
            self.name = self.name.strip()
        super().save(*args, **kwargs)


class Service(models.Model):
    """
    External service belonging to the same product ecosystem.

    Administrators register sibling sites (academy, shop, blog, dashboard,
    and so on). Templates render them by location ``key`` via the
    ``{% ecosystem %}`` inclusion tag.
    """

    location = models.ForeignKey(
        Location,
        verbose_name=_("location"),
        related_name="services",
        on_delete=models.PROTECT,
        help_text=_(
            "Placement this service belongs to. Must match a location key "
            "used in the ecosystem template tag."
        ),
    )
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
    position = models.PositiveIntegerField(
        _("position"),
        default=0,
        help_text=_(
            "Order within the location. Maintained by the application; "
            "lower values appear first."
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
        ordering = ("position", "name")
        indexes = [
            models.Index(
                fields=["location", "position"],
                name="ecosystem_svc_loc_pos_idx",
            ),
            models.Index(
                fields=["location", "active", "position"],
                name="ecosystem_svc_loc_active_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(slug=""),
                name="ecosystem_svc_slug_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generate a slug when the field is empty."""
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
