"""Data models for ecosystem locations and services."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Location(models.Model):
    """
    Named placement for ecosystem services (for example Footer or Header).

    ``key`` is the stable template-tag identifier used by
    ``{% ecosystem "key" %}``. Surrounding whitespace is stripped on
    validation and save. Changing an existing key is a breaking change for
    every template that still references the old value.
    """

    key = models.CharField(
        _("key"),
        max_length=100,
        unique=True,
        help_text=_(
            'Stable template-tag identifier (for example "footer" or '
            '"pricing_page"). Must match the ecosystem template tag '
            "argument exactly. Changing an existing key breaks those "
            "template usages. Surrounding whitespace is trimmed "
            "automatically."
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

    def clean(self) -> None:
        """Validate and normalize key/name before form or Admin saves."""
        super().clean()
        key = (self.key or "").strip()
        if not key:
            raise ValidationError(
                {
                    "key": _(
                        'Enter a location key (for example "footer"). '
                        "Blank or whitespace-only keys are not allowed."
                    )
                }
            )
        self.key = key

        name = (self.name or "").strip()
        self.name = name or key

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Normalize key and name before persisting.

        Stripping is intentional normalization of surrounding whitespace, not a
        rewrite of the key identity. Prefer ``full_clean()`` (Admin/forms) so
        blank keys raise a validation error instead of hitting the DB check.
        """
        self.key = (self.key or "").strip()
        name = (self.name or "").strip()
        self.name = name or self.key
        super().save(*args, **kwargs)


class Service(models.Model):
    """
    External service belonging to the same product ecosystem.

    Administrators register sibling sites (academy, shop, blog, dashboard,
    and so on). Templates render them by location ``key`` via the
    ``{% ecosystem %}`` inclusion tag.

    ``position`` is system-managed dense order within a location
    (``0..n-1``). Write helpers own create/move/reorder/delete so Admin and
    forms must not treat position as an editable field. Uniqueness of
    ``(location, position)`` is an application invariant rather than a DB
    constraint, so reorder/swap updates can complete without transient
    collisions.
    """

    location = models.ForeignKey(
        Location,
        verbose_name=_("location"),
        related_name="services",
        on_delete=models.PROTECT,
        help_text=_(
            "Placement this service belongs to. The placement key must match "
            "the argument used in the ecosystem template tag."
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
            "Order within the location. Managed automatically — use the "
            "location workspace to reorder. Lower values appear first."
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
        ordering = ("position", "pk")
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

    def clean(self) -> None:
        """Normalize slug whitespace; empty slug is filled in ``save()``."""
        super().clean()
        if self.slug is not None:
            self.slug = str(self.slug).strip()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generate a slug when the field is empty (no ordering side effects)."""
        if self.slug is not None:
            self.slug = str(self.slug).strip()
        if not self.slug:
            self.slug = type(self).build_unique_slug(
                self.name,
                exclude_pk=self.pk,
            )
        super().save(*args, **kwargs)

    @classmethod
    def build_unique_slug(
        cls,
        name: str,
        *,
        exclude_pk: int | None = None,
    ) -> str:
        """Canonical unique slug builder used by model save and Admin forms."""
        base_slug = slugify(name) or "service"
        candidate = base_slug
        suffix = 2
        queryset = cls._default_manager.all()
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        while queryset.filter(slug=candidate).exists():
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        return candidate
