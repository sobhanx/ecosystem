"""ServiceAdmin — secondary global search and detailed edits."""

from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..forms import ServiceAdminForm
from ..models import Service
from ..services import (
    delete_service,
    delete_services,
    duplicate_services as bulk_duplicate_services,
    move_services,
    quick_add_service,
    set_services_active,
)
from .helpers import boolean_badge, workspace_url


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Secondary admin for global search and detailed edits.

    Ordering is owned by the location workspace; ``position`` is read-only here.
    """

    form = ServiceAdminForm
    list_display = (
        "logo_thumbnail",
        "name",
        "location_link",
        "url_link",
        "active_badge",
        "new_tab_badge",
        "updated_at",
    )
    list_display_links = ("name",)
    list_filter = ("active", "open_in_new_tab", "location", "updated_at")
    search_fields = (
        "name",
        "slug",
        "url",
        "location__key",
        "location__name",
        "description",
    )
    ordering = ("location__position", "position", "pk")
    autocomplete_fields = ("location",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "position",
        "logo_preview",
        "created_at",
        "updated_at",
    )
    list_per_page = 25
    list_max_show_all = 200
    save_on_top = True
    empty_value_display = "—"
    actions = (
        "activate_services",
        "deactivate_services",
        "duplicate_services",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Service]:
        return super().get_queryset(request).select_related("location")

    fieldsets = (
        (
            _("Service"),
            {
                "fields": ("name", "url", "description"),
                "description": _(
                    "Basic details visitors see when this service is listed."
                ),
            },
        ),
        (
            _("Placement"),
            {
                "fields": ("location", "active", "position"),
                "description": _(
                    "Prefer the location workspace for ordering. Position is "
                    "read-only on this form."
                ),
            },
        ),
        (
            _("Logo"),
            {
                "fields": ("logo", "logo_preview"),
                "description": _(
                    "Optional image shown next to the service name. "
                    "Save the form to refresh the preview after uploading."
                ),
            },
        ),
        (
            _("Link behavior"),
            {
                "fields": ("open_in_new_tab",),
            },
        ),
        (
            _("Advanced"),
            {
                "classes": ("collapse",),
                "fields": ("slug",),
                "description": _(
                    "Technical identifiers. Most editors can leave these alone."
                ),
            },
        ),
        (
            _("Timestamps"),
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def save_model(
        self,
        request: HttpRequest,
        obj: Service,
        form: ServiceAdminForm,
        change: bool,
    ) -> None:
        """
        Append new services via the service layer.

        Location changes go through ``move_services`` so dense ordering is kept
        on both the source and destination placements.
        """
        if not change:
            created = quick_add_service(
                obj.location,
                obj.name,
                obj.url,
                active=obj.active,
                open_in_new_tab=obj.open_in_new_tab,
                description=obj.description or "",
                slug=obj.slug or "",
                logo=obj.logo if getattr(obj, "logo", None) else "",
            )
            obj.pk = created.pk
            obj.position = created.position
            form.instance = created
            return

        previous = Service.objects.get(pk=obj.pk)
        new_location = obj.location
        location_changed = previous.location_id != new_location.pk

        # Persist non-ordering fields while keeping the previous placement.
        obj.location_id = previous.location_id
        obj.position = previous.position
        super().save_model(request, obj, form, change)

        if location_changed:
            move_services([obj], new_location)
            obj.refresh_from_db()
            form.instance = obj

    def delete_model(self, request: HttpRequest, obj: Service) -> None:
        """Delete via the service layer so sibling positions stay dense."""
        delete_service(obj)

    def delete_queryset(
        self,
        request: HttpRequest,
        queryset: QuerySet[Service],
    ) -> None:
        """Bulk-delete via the service layer so each location is renumbered."""
        delete_services(queryset)

    @admin.display(description=_("Location"), ordering="location__name")
    def location_link(self, obj: Service) -> str:
        if not obj.location_id:
            return "—"
        return format_html(
            '<a href="{}">{}</a>',
            workspace_url(obj.location_id),
            obj.location,
        )

    @admin.display(description=_("URL"), ordering="url")
    def url_link(self, obj: Service) -> str:
        if not obj.url:
            return "—"
        label = obj.url if len(obj.url) <= 48 else f"{obj.url[:45]}…"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            obj.url,
            label,
        )

    @admin.display(description=_("Active"), ordering="active")
    def active_badge(self, obj: Service) -> str:
        return boolean_badge(obj.active, yes=_("Active"), no=_("Hidden"))

    @admin.display(description=_("New tab"), ordering="open_in_new_tab")
    def new_tab_badge(self, obj: Service) -> str:
        return boolean_badge(
            obj.open_in_new_tab,
            yes=_("New tab"),
            no=_("Same tab"),
        )

    @admin.display(description=_("Logo"))
    def logo_thumbnail(self, obj: Service) -> str:
        """Compact logo for the changelist."""
        return self._render_logo(obj, max_height=28, max_width=56)

    @admin.display(description=_("Logo preview"))
    def logo_preview(self, obj: Service) -> str:
        """Larger logo preview on the change form."""
        return self._render_logo(obj, max_height=96, max_width=192)

    def _render_logo(
        self,
        obj: Service,
        *,
        max_height: int,
        max_width: int,
    ) -> str:
        """Render a safe, contained logo thumbnail or an em dash."""
        if not getattr(obj, "pk", None) or not getattr(obj, "logo", None):
            return "—"
        try:
            url = obj.logo.url
        except (ValueError, OSError):
            return "—"
        return format_html(
            '<img src="{}" alt="" '
            'style="max-height:{}px;max-width:{}px;width:auto;height:auto;'
            "object-fit:contain;display:block;"
            "background:#f8f8f8;border:1px solid #e0e0e0;"
            'border-radius:4px;padding:4px;" />',
            url,
            max_height,
            max_width,
        )

    @admin.action(description=_("Activate selected services"))
    def activate_services(
        self,
        request: HttpRequest,
        queryset: QuerySet[Service],
    ) -> None:
        updated = set_services_active(queryset, True)
        self.message_user(
            request,
            ngettext(
                "%d service was activated.",
                "%d services were activated.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Deactivate selected services"))
    def deactivate_services(
        self,
        request: HttpRequest,
        queryset: QuerySet[Service],
    ) -> None:
        updated = set_services_active(queryset, False)
        self.message_user(
            request,
            ngettext(
                "%d service was deactivated.",
                "%d services were deactivated.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Duplicate selected services"))
    def duplicate_services(
        self,
        request: HttpRequest,
        queryset: QuerySet[Service],
    ) -> None:
        created = len(bulk_duplicate_services(list(queryset.order_by("pk"))))
        self.message_user(
            request,
            ngettext(
                "%d service was duplicated.",
                "%d services were duplicated.",
                created,
            )
            % created,
            messages.SUCCESS,
        )
