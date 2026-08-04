"""Location workspace and reorder endpoints for LocationAdmin."""

from __future__ import annotations

import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..forms import WorkspaceQuickAddForm
from ..lookups import (
    get_location_services_by_ids,
    get_service_for_location,
    get_services_for_location,
)
from ..models import Location, Service
from ..services import (
    delete_service,
    duplicate_service,
    duplicate_services,
    move_service_down,
    move_service_to_bottom,
    move_service_to_top,
    move_service_up,
    move_services,
    quick_add_service,
    reorder_services,
    set_services_active,
)
from .helpers import reorder_url, workspace_url


class LocationWorkspaceMixin:
    """Workspace routes and POST handlers mixed into LocationAdmin."""

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

    def workspace_view(
        self,
        request: HttpRequest,
        object_id: str,
    ) -> HttpResponse:
        """Location workspace: quick add, ordered list, nudge actions."""
        location = get_object_or_404(self.get_queryset(request), pk=object_id)
        if not self.has_change_permission(request, location):
            raise PermissionDenied

        quick_add_form = WorkspaceQuickAddForm()

        if request.method == "POST":
            action = request.POST.get("workspace_action", "")
            redirect = HttpResponseRedirect(workspace_url(location.pk))

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
                return self._render_workspace(
                    request, location, quick_add_form=quick_add_form
                )

            if action.startswith("bulk_"):
                try:
                    self._handle_workspace_bulk_action(request, location, action)
                except ValidationError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
                return redirect

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

        return self._render_workspace(request, location, quick_add_form=quick_add_form)

    def _render_workspace(
        self,
        request: HttpRequest,
        location: Location,
        *,
        quick_add_form: WorkspaceQuickAddForm | None = None,
    ) -> HttpResponse:
        services = list(get_services_for_location(location))
        other_locations = list(
            self.get_queryset(request)
            .exclude(pk=location.pk)
            .order_by("position", "name")
        )
        active_count = sum(1 for service in services if service.active)
        context = {
            **self.admin_site.each_context(request),
            "title": _("Workspace: %(name)s") % {"name": location.name},
            "opts": self.opts,
            "location": location,
            "services": services,
            "service_total": len(services),
            "service_active_count": active_count,
            "other_locations": other_locations,
            "quick_add_form": quick_add_form or WorkspaceQuickAddForm(),
            "reorder_url": reorder_url(location.pk),
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
                {
                    "ok": False,
                    "error": gettext(
                        "Could not save order. Refresh the page and try again, "
                        "or use the move buttons."
                    ),
                },
                status=405,
            )

        location = get_object_or_404(self.get_queryset(request), pk=object_id)
        if not self.has_change_permission(request, location):
            return JsonResponse(
                {
                    "ok": False,
                    "error": gettext(
                        "You do not have permission to reorder services."
                    ),
                },
                status=403,
            )

        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            return JsonResponse(
                {
                    "ok": False,
                    "error": gettext(
                        "Could not save order. Refresh the page and try again, "
                        "or use the move buttons."
                    ),
                },
                status=400,
            )

        ordered_ids = payload.get("ordered_ids")
        if not isinstance(ordered_ids, list):
            return JsonResponse(
                {
                    "ok": False,
                    "error": gettext(
                        "Could not save order. Refresh the page and try again, "
                        "or use the move buttons."
                    ),
                },
                status=400,
            )

        try:
            normalized_ids = [int(pk) for pk in ordered_ids]
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "ok": False,
                    "error": gettext(
                        "Could not save order. Refresh the page and try again, "
                        "or use the move buttons."
                    ),
                },
                status=400,
            )

        try:
            reorder_services(location, normalized_ids)
        except ValidationError:
            return JsonResponse(
                {
                    "ok": False,
                    "error": gettext(
                        "Could not save order. Refresh the page and try again, "
                        "or use the move buttons."
                    ),
                },
                status=400,
            )

        return JsonResponse({"ok": True})

    def _workspace_selected_services(
        self,
        request: HttpRequest,
        location: Location,
    ) -> list[Service] | None:
        raw_ids = request.POST.getlist("service_ids")
        if not raw_ids:
            self.message_user(
                request,
                _("Select at least one service."),
                messages.ERROR,
            )
            return None
        try:
            ids = [int(pk) for pk in raw_ids]
        except (TypeError, ValueError):
            self.message_user(request, _("Invalid service selection."), messages.ERROR)
            return None
        services = get_location_services_by_ids(location, ids)
        if len(services) != len(set(ids)):
            self.message_user(
                request,
                _("One or more selected services do not belong to this location."),
                messages.ERROR,
            )
            return None
        return services

    def _handle_workspace_bulk_action(
        self,
        request: HttpRequest,
        location: Location,
        action: str,
    ) -> None:
        services = self._workspace_selected_services(request, location)
        if services is None:
            return

        count = len(services)
        if action == "bulk_activate":
            set_services_active(services, True)
            self.message_user(
                request,
                ngettext(
                    "%d service was activated.",
                    "%d services were activated.",
                    count,
                )
                % count,
                messages.SUCCESS,
            )
            return
        if action == "bulk_deactivate":
            set_services_active(services, False)
            self.message_user(
                request,
                ngettext(
                    "%d service was deactivated.",
                    "%d services were deactivated.",
                    count,
                )
                % count,
                messages.SUCCESS,
            )
            return
        if action == "bulk_duplicate":
            duplicate_services(services)
            self.message_user(
                request,
                ngettext(
                    "%d service was duplicated.",
                    "%d services were duplicated.",
                    count,
                )
                % count,
                messages.SUCCESS,
            )
            return
        if action == "bulk_move":
            target_id = request.POST.get("target_location")
            if not target_id:
                self.message_user(
                    request,
                    _("Choose a destination location."),
                    messages.ERROR,
                )
                return
            try:
                target = (
                    self.get_queryset(request)
                    .exclude(pk=location.pk)
                    .get(pk=target_id)
                )
            except (Location.DoesNotExist, ValueError, TypeError):
                self.message_user(
                    request,
                    _("Choose a valid destination location."),
                    messages.ERROR,
                )
                return
            if not self.has_change_permission(request, target):
                self.message_user(
                    request,
                    _("You do not have permission to move services to that location."),
                    messages.ERROR,
                )
                return
            moved = move_services(services, target)
            moved_count = len(moved)
            self.message_user(
                request,
                ngettext(
                    "%(count)d service was moved to “%(name)s”.",
                    "%(count)d services were moved to “%(name)s”.",
                    moved_count,
                )
                % {"count": moved_count, "name": target.name},
                messages.SUCCESS,
            )
            return

        self.message_user(request, _("Unknown action."), messages.ERROR)

    def _workspace_service_or_none(
        self,
        request: HttpRequest,
        location: Location,
        service_id: str | None,
    ) -> Service | None:
        if not service_id:
            self.message_user(request, _("Missing service."), messages.ERROR)
            return None
        service = get_service_for_location(location, service_id)
        if service is None:
            self.message_user(
                request,
                _("That service does not belong to this location."),
                messages.ERROR,
            )
            return None
        return service

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
