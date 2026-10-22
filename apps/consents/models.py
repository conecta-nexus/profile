import uuid

from django.db import models
from django.db.models import Q


class DataConsent(models.Model):
    """Store explicit legal consent registration under Colombian Law 1581 of 2012 (Habeas Data)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Logical correlation to db_auth users.id without physical foreign key
    user_id = models.UUIDField(db_index=True)

    policy_version = models.CharField(max_length=20, default="v1.0-2026")
    is_accepted = models.BooleanField(default=True)

    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_consents"
        ordering = ["-accepted_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(is_accepted=True),
                name="consent_must_be_accepted",
            ),
        ]

    def __str__(self) -> str:
        """Return a readable representation of the data consent record."""
        return f"Consent({self.user_id}, {self.policy_version}, {self.accepted_at})"
