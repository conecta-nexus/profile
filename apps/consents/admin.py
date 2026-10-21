from django.contrib import admin

from apps.consents.models import DataConsent


@admin.register(DataConsent)
class DataConsentAdmin(admin.ModelAdmin):
    """Admin configuration for inspecting Law 1581 Habeas Data consents."""

    list_display = (
        "id",
        "user_id",
        "policy_version",
        "is_accepted",
        "ip_address",
        "accepted_at",
    )
    list_filter = ("policy_version", "is_accepted", "accepted_at")
    search_fields = ("user_id", "ip_address", "user_agent")
    readonly_fields = (
        "id",
        "user_id",
        "policy_version",
        "is_accepted",
        "ip_address",
        "user_agent",
        "accepted_at",
    )

    def has_add_permission(self, request) -> bool:
        # Legal consents must be registered via the API, not manually created
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        # Auditable legal log; prevent accidental deletions
        return False
