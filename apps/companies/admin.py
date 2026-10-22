from django.contrib import admin

from apps.companies.models import CompanyProfile


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    """Configure company profiles for administrative inspection."""

    list_display = (
        "business_name",
        "nit",
        "economic_sector",
        "is_verified",
        "created_at",
    )
    search_fields = (
        "business_name",
        "nit",
        "contact_email",
    )
    list_filter = (
        "is_verified",
        "economic_sector",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )