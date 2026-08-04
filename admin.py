"""Django Admin configuration for ecosystem locations and services.

Location is the primary editorial surface. ServiceAdmin remains available for
global search and rare edits. Ordering mutations belong in ``services.py``;
the Location workspace UI is intentionally deferred.
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .forms import ServiceAdminForm
from .models import Location, Service
from .services import duplicate_service, quick_add_service, set_services_active


def _boolean_badge(value: bool, *, yes: str, no: str) -> str:
    """Render a compact active/hidden badge."""
    if value:
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            "background:#e7f8ed;color:#0b6b2f;font-size:12px;font-weight:600;"
            '">{}</span>',
            yes,
        )
    return format_html(
        '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
        "background:#f4f4f4;color:#666;font-size:12px;font-weight:600;"
        '">{}</span>',
        no,
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Primary admin for placements editors manage day to day."""

    list_display = (
        "name",
        "key",
        "active_badge",
        "service_count",
        "active_service_count",
        "manage_services_link",
        "updated_at",
    )
    list_display_links = ("name",)
    list_filter = ("active", "updated_at")
    search_fields = ("name", "key", "description")
    ordering = ("position", "name")
    readonly_fields = ("created_at", "updated_at", "template_tag_snippet")
    list_per_page = 50
    list_max_show_all = 200
    save_on_top = True
    empty_value_display = "—"
    actions = ("activate_locations", "deactivate_locations")

    fieldsets = (
        (
            _("Placement"),
            {
                "fields": ("name", "key", "description", "active", "position"),
                "description": _(
                    "Locations are the placements rendered by the ecosystem "
                    "template tag. Create a location first, then add services."
                ),
            },
        ),
        (
            _("Template tag"),
            {
                "fields": ("template_tag_snippet",),
                "description": _(
                    "Use this key in templates. Prefer not renaming the key "
                    "after templates already reference it."
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

    def get_queryset(self, request: HttpRequest) -> QuerySet[Location]:
        return (
            super()
            .get_queryset(request)
            .annotate(
                _service_count=Count("services", distinct=True),
                _active_service_count=Count(
                    "services",
                    filter=Q(services__active=True),
                    distinct=True,
                ),
            )
        )

    @admin.display(description=_("Active"), ordering="active")
    def active_badge(self, obj: Location) -> str:
        return _boolean_badge(
            obj.active,
            yes=_("Active"),
            no=_("Hidden"),
        )

    @admin.display(description=_("Services"), ordering="_service_count")
    def service_count(self, obj: Location) -> int:
        return int(getattr(obj, "_service_count", 0))

    @admin.display(description=_("Active services"), ordering="_active_service_count")
    def active_service_count(self, obj: Location) -> int:
        return int(getattr(obj, "_active_service_count", 0))

    @admin.display(description=_("Manage"))
    def manage_services_link(self, obj: Location) -> str:
        if not obj.pk:
            return "—"
        opts = Service._meta
        try:
            url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        except NoReverseMatch:
            url = f"/admin/{opts.app_label}/{opts.model_name}/"
        return format_html(
            '<a class="button" href="{}?location__id__exact={}">{}</a>',
            url,
            obj.pk,
            _("Manage services"),
        )

    @admin.display(description=_("Template tag"))
    def template_tag_snippet(self, obj: Location) -> str:
        if not obj.key:
            return "—"
        return format_html(
            "<code>{{% ecosystem \"{}\" %}}</code>",
            obj.key,
        )

    @admin.action(description=_("Activate selected locations"))
    def activate_locations(
        self,
        request: HttpRequest,
        queryset: QuerySet[Location],
    ) -> None:
        updated = queryset.update(active=True)
        self.message_user(
            request,
            ngettext(
                "%d location was activated.",
                "%d locations were activated.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Deactivate selected locations"))
    def deactivate_locations(
        self,
        request: HttpRequest,
        queryset: QuerySet[Location],
    ) -> None:
        updated = queryset.update(active=False)
        self.message_user(
            request,
            ngettext(
                "%d location was deactivated.",
                "%d locations were deactivated.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Secondary admin for global search and detailed edits.

    Ordering is owned by the location; ``position`` is read-only here.
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
    ordering = ("location__position", "position", "name")
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
                    "Choose a location. Order within a location is managed "
                    "from that location (workspace coming next); position is "
                    "shown here as read-only."
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
        """Append new services; never let the change form rewrite position."""
        if change:
            obj.position = (
                Service.objects.only("position").get(pk=obj.pk).position
            )
            super().save_model(request, obj, form, change)
            return

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

    @admin.display(description=_("Location"), ordering="location__name")
    def location_link(self, obj: Service) -> str:
        if not obj.location_id:
            return "—"
        opts = Location._meta
        try:
            url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=[obj.location_id],
            )
        except NoReverseMatch:
            url = f"/admin/{opts.app_label}/{opts.model_name}/{obj.location_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.location)

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
        return _boolean_badge(obj.active, yes=_("Active"), no=_("Hidden"))

    @admin.display(description=_("New tab"), ordering="open_in_new_tab")
    def new_tab_badge(self, obj: Service) -> str:
        return _boolean_badge(
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
        created = 0
        for service in queryset.order_by("pk"):
            duplicate_service(service)
            created += 1
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
