from rest_framework import serializers

from apps.consents.models import DataConsent


class DataConsentCreateSerializer(serializers.ModelSerializer):
    """Validate explicit user consent registration under Law 1581 of 2012."""

    is_accepted = serializers.BooleanField(required=True)
    policy_version = serializers.CharField(
        max_length=20,
        default="v1.0-2026",
        required=False,
    )

    class Meta:
        model = DataConsent
        fields = ("policy_version", "is_accepted")

    def validate_is_accepted(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError(
                "Consent must be explicitly accepted (is_accepted must be true)."
            )
        return value

    def validate_policy_version(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Policy version cannot be blank.")
        return value


class DataConsentStatusSerializer(serializers.ModelSerializer):
    """Serialize data consent acceptance record for status inspection."""

    class Meta:
        model = DataConsent
        fields = (
            "id",
            "user_id",
            "policy_version",
            "is_accepted",
            "accepted_at",
        )
        read_only_fields = fields
