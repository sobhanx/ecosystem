"""LocationAdmin — primary editorial surface for placements."""

from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..models import Location
from .helpers import boolean_badge, workspace_url
from .workspace import LocationWorkspaceMixin


@admin.register(Location)
class LocationAdmin(LocationWorkspaceMixin, admin.ModelAdmin):
    """Primary admin for placements, including the Location workspace."""

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
    readonly_fields = (
        "created_at",
        "updated_at",
        "template_tag_snippet",
        "workspace_link",
    )
    list_per_page = 50
    list_max_show_all = 200
    save_on_top = True
    empty_value_display = "—"
    actions = ("activate_locations", "deactivate_locations")

    class Media:
        js = ("ecosystem/admin_copy.js",)

    fieldsets = (
        (
            _("Placement"),
            {
                "fields": ("name", "key", "description", "active", "position"),
                "description": _(
                    "Locations are the placements rendered by the ecosystem "
                    "template tag. Create a location first, then manage its "
                    "services from the workspace."
                ),
            },
        ),
        (
            _("Workspace"),
            {
                "fields": ("workspace_link", "template_tag_snippet"),
                "description": _(
                    "Use the workspace to add, reorder, activate, and "
                    "duplicate services for this placement."
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

    def response_add(self, request, obj, post_url_continue=None):
        """Send editors into the workspace after creating a location."""
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            return HttpResponseRedirect(workspace_url(obj.pk))
        return super().response_add(request, obj, post_url_continue)

    @admin.display(description=_("Active"), ordering="active")
    def active_badge(self, obj: Location) -> str:
        return boolean_badge(
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
        return format_html(
            '<a class="button" href="{}">{}</a>',
            workspace_url(obj.pk),
            _("Open workspace"),
        )

    @admin.display(description=_("Workspace"))
    def workspace_link(self, obj: Location) -> str:
        if not obj.pk:
            return "—"
        return format_html(
            '<a class="button" href="{}">{}</a>',
            workspace_url(obj.pk),
            _("Open workspace"),
        )

    @admin.display(description=_("Template tag"))
    def template_tag_snippet(self, obj: Location) -> str:
        if not obj.key:
            return "—"
        tag = '{% ecosystem "' + obj.key + '" %}'
        return format_html(
            '<code class="eco-admin-tag">{}</code> '
            '<button type="button" class="button eco-copy-snippet" '
            'data-copy="{}" data-copied-label="{}">{}</button>',
            tag,
            tag,
            _("Copied"),
            _("Copy"),
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
