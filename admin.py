"""Django Admin configuration for ecosystem locations and services.

Location is the primary editorial surface, including a per-location workspace.
ServiceAdmin remains available for global search and rare edits. Ordering
mutations belong in ``services.py``.
"""

from __future__ import annotations

import json

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import NoReverseMatch, path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .forms import ServiceAdminForm, WorkspaceQuickAddForm
from .models import Location, Service
from .services import (
    delete_service,
    duplicate_service,
    move_service_down,
    move_service_to_bottom,
    move_service_to_top,
    move_service_up,
    quick_add_service,
    reorder_services,
    set_services_active,
)


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


def _workspace_url(location_id: int) -> str:
    try:
        return reverse("admin:ecosystem_location_workspace", args=[location_id])
    except NoReverseMatch:
        return f"/admin/ecosystem/location/{location_id}/workspace/"


def _reorder_url(location_id: int) -> str:
    try:
        return reverse("admin:ecosystem_location_reorder", args=[location_id])
    except NoReverseMatch:
        return f"/admin/ecosystem/location/{location_id}/reorder/"


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
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

    def get_urls(self):
        info = self.opts.app_label, self.opts.model_name
        custom = [
            path(
                "<path:object_id>/workspace/",
                self.admin_site.admin_view(self.workspace_view),
                name="%s_%s_workspace" % info,
            ),
            path(
                "<path:object_id>/reorder/",
                self.admin_site.admin_view(self.reorder_view),
                name="%s_%s_reorder" % info,
            ),
        ]
        return custom + super().get_urls()

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
            return HttpResponseRedirect(_workspace_url(obj.pk))
        return super().response_add(request, obj, post_url_continue)

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
        return format_html(
            '<a class="button" href="{}">{}</a>',
            _workspace_url(obj.pk),
            _("Open workspace"),
        )

    @admin.display(description=_("Workspace"))
    def workspace_link(self, obj: Location) -> str:
        if not obj.pk:
            return "—"
        return format_html(
            '<a class="button" href="{}">{}</a>',
            _workspace_url(obj.pk),
            _("Open workspace"),
        )

    @admin.display(description=_("Template tag"))
    def template_tag_snippet(self, obj: Location) -> str:
        if not obj.key:
            return "—"
        return format_html(
            "<code>{{% ecosystem \"{}\" %}}</code>",
            obj.key,
        )

    def workspace_view(
        self,
        request: HttpRequest,
        object_id: str,
    ) -> HttpResponse:
        """Location workspace: quick add, ordered list, nudge actions."""
        location = get_object_or_404(self.get_queryset(request), pk=object_id)
        if not self.has_change_permission(request, location):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        quick_add_form = WorkspaceQuickAddForm()

        if request.method == "POST":
            action = request.POST.get("workspace_action", "")
            redirect = HttpResponseRedirect(_workspace_url(location.pk))

            if action == "quick_add":
                quick_add_form = WorkspaceQuickAddForm(request.POST)
                if quick_add_form.is_valid():
                    quick_add_service(
                        location,
                        quick_add_form.cleaned_data["name"],
                        str(quick_add_form.cleaned_data["url"]),
                    )
                    self.message_user(
                        request,
                        _("Service “%(name)s” was added.")
                        % {"name": quick_add_form.cleaned_data["name"]},
                        messages.SUCCESS,
                    )
                    return redirect
            else:
                service = self._workspace_service_or_none(
                    request, location, request.POST.get("service_id")
                )
                if service is None:
                    return redirect
                try:
                    self._handle_workspace_service_action(
                        request, location, service, action
                    )
                except ValidationError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
                return redirect

        services = list(
            Service.objects.filter(location=location).order_by("position", "pk")
        )
        context = {
            **self.admin_site.each_context(request),
            "title": _("Workspace: %(name)s") % {"name": location.name},
            "opts": self.opts,
            "location": location,
            "services": services,
            "quick_add_form": quick_add_form,
            "reorder_url": _reorder_url(location.pk),
            "has_view_permission": self.has_view_permission(request, location),
            "has_change_permission": self.has_change_permission(request, location),
        }
        return render(request, "admin/ecosystem/location_workspace.html", context)

    def reorder_view(
        self,
        request: HttpRequest,
        object_id: str,
    ) -> JsonResponse:
        """JSON endpoint: persist drag-and-drop order via ``reorder_services``."""
        if request.method != "POST":
            return JsonResponse(
                {"ok": False, "error": gettext("POST required.")},
                status=405,
            )

        location = get_object_or_404(Location, pk=object_id)
        if not self.has_change_permission(request, location):
            return JsonResponse(
                {"ok": False, "error": gettext("Permission denied.")},
                status=403,
            )

        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            return JsonResponse(
                {"ok": False, "error": gettext("Malformed JSON payload.")},
                status=400,
            )

        ordered_ids = payload.get("ordered_ids")
        if not isinstance(ordered_ids, list):
            return JsonResponse(
                {
                    "ok": False,
                    "error": gettext("ordered_ids must be a list of service IDs."),
                },
                status=400,
            )

        try:
            normalized_ids = [int(pk) for pk in ordered_ids]
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "ok": False,
                    "error": gettext("ordered_ids must contain integers only."),
                },
                status=400,
            )

        try:
            reorder_services(location, normalized_ids)
        except ValidationError as exc:
            message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return JsonResponse({"ok": False, "error": message}, status=400)

        return JsonResponse({"ok": True})

    def _workspace_service_or_none(
        self,
        request: HttpRequest,
        location: Location,
        service_id: str | None,
    ) -> Service | None:
        if not service_id:
            self.message_user(request, _("Missing service."), messages.ERROR)
            return None
        try:
            return Service.objects.get(pk=service_id, location=location)
        except Service.DoesNotExist:
            self.message_user(
                request,
                _("That service does not belong to this location."),
                messages.ERROR,
            )
            return None

    def _handle_workspace_service_action(
        self,
        request: HttpRequest,
        location: Location,
        service: Service,
        action: str,
    ) -> None:
        if action == "toggle_active":
            set_services_active([service], not service.active)
            self.message_user(
                request,
                _("Service “%(name)s” was updated.") % {"name": service.name},
                messages.SUCCESS,
            )
            return
        if action == "duplicate":
            copy = duplicate_service(service)
            self.message_user(
                request,
                _("Duplicated “%(name)s”.") % {"name": copy.name},
                messages.SUCCESS,
            )
            return
        if action == "delete":
            name = service.name
            delete_service(service)
            self.message_user(
                request,
                _("Service “%(name)s” was deleted.") % {"name": name},
                messages.SUCCESS,
            )
            return
        if action == "move_up":
            move_service_up(service)
        elif action == "move_down":
            move_service_down(service)
        elif action == "move_top":
            move_service_to_top(service)
        elif action == "move_bottom":
            move_service_to_bottom(service)
        else:
            self.message_user(request, _("Unknown action."), messages.ERROR)
            return
        self.message_user(request, _("Order updated."), messages.SUCCESS)

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
        return format_html(
            '<a href="{}">{}</a>',
            _workspace_url(obj.location_id),
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
