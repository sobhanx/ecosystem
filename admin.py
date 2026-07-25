"""Django Admin configuration for ecosystem services."""

from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .forms import ServiceAdminForm
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Admin interface for managing ecosystem services."""

    form = ServiceAdminForm
    list_display = (
        "logo_thumbnail",
        "name",
        "location",
        "display_order",
        "active",
        "open_in_new_tab",
        "updated_at",
    )
    list_display_links = ("name",)
    list_editable = ("display_order", "active")
    list_filter = ("active", "open_in_new_tab", "location", "updated_at")
    search_fields = ("name", "slug", "url", "location", "description")
    ordering = ("display_order", "name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("logo_preview", "created_at", "updated_at")
    list_per_page = 25
    list_max_show_all = 200
    save_on_top = True
    empty_value_display = "—"
    actions = ("activate_services", "deactivate_services")

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
                "fields": ("location", "display_order", "active"),
                "description": _(
                    "Control where the service appears and whether it is "
                    "visible. Placement keys must match the value passed to "
                    "the ecosystem template tag."
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
        updated = queryset.update(active=True)
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
        updated = queryset.update(active=False)
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
