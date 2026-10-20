import uuid

from django.db import models


class CompanyProfile(models.Model):
    """Store the corporate profile owned by a company user."""

    # Preserve database-per-service isolation through a logical UUID reference.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(unique=True)

    nit = models.CharField(max_length=25, unique=True)
    business_name = models.CharField(max_length=200)
    economic_sector = models.CharField(max_length=100)
    description = models.TextField()

    website_url = models.URLField(null=True, blank=True)
    public_links = models.JSONField(default=list, blank=True)

    contact_name = models.CharField(max_length=150)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=25)

    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_profiles"

    def __str__(self):
        """Return the business name and its corporate identifier."""
        return f"{self.business_name} ({self.nit})"