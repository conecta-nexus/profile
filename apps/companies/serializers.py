from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.companies.models import CompanyProfile
from apps.companies.validators import validate_colombian_nit


class RejectUnknownFieldsMixin:
    """Reject fields that are not explicitly supported by a serializer."""

    def to_internal_value(self, data):
        unknown_fields = set(data.keys()) - set(self.fields.keys())

        if unknown_fields:
            raise serializers.ValidationError(
                {
                    field: ["This field is not supported."]
                    for field in sorted(unknown_fields)
                }
            )

        return super().to_internal_value(data)


class CompanyProfileCreateSerializer(
    RejectUnknownFieldsMixin,
    serializers.ModelSerializer,
):
    """Validate the initial registration of a company profile."""

    nit = serializers.CharField(
        max_length=25,
        validators=[
            validate_colombian_nit,
            UniqueValidator(queryset=CompanyProfile.objects.all()),
        ],
    )
    public_links = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "user_id",
            "nit",
            "business_name",
            "economic_sector",
            "description",
            "website_url",
            "public_links",
            "contact_name",
            "contact_email",
            "contact_phone",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "is_verified",
            "created_at",
            "updated_at",
        )


class CompanyProfileUpdateSerializer(
    RejectUnknownFieldsMixin,
    serializers.ModelSerializer,
):
    """Update mutable company information while protecting the NIT."""

    public_links = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = CompanyProfile
        fields = (
            "economic_sector",
            "description",
            "website_url",
            "public_links",
            "contact_name",
            "contact_email",
            "contact_phone",
        )
        extra_kwargs = {
            "economic_sector": {"required": False},
            "description": {"required": False},
            "website_url": {"required": False},
            "contact_name": {"required": False},
            "contact_email": {"required": False},
            "contact_phone": {"required": False},
        }

    def to_internal_value(self, data):
        # A validated NIT cannot be changed through profile updates.
        if "nit" in data:
            raise serializers.ValidationError(
                {"nit": ["This field is immutable."]}
            )

        return super().to_internal_value(data)


class CompanyProfilePrivateSerializer(serializers.ModelSerializer):
    """Return the complete company profile to its owner."""

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "user_id",
            "nit",
            "business_name",
            "economic_sector",
            "description",
            "website_url",
            "public_links",
            "contact_name",
            "contact_email",
            "contact_phone",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CompanyProfilePublicSerializer(serializers.ModelSerializer):
    """Return company information without its private contact channels."""

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "user_id",
            "nit",
            "business_name",
            "economic_sector",
            "description",
            "website_url",
            "public_links",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields