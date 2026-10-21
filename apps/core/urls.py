from django.urls import include, path

from apps.consents.views import ConsentRegistrationView, ConsentStatusView
from apps.core.views import InternalEligibilityView

urlpatterns = [
    path("consents/", include("apps.consents.urls")),
    path("consent", ConsentRegistrationView.as_view(), name="consent-direct"),
    path("consent/", ConsentRegistrationView.as_view(), name="consent-direct-slash"),
    path("consent/me", ConsentStatusView.as_view(), name="consent-status-direct"),
    path("consent/me/", ConsentStatusView.as_view(), name="consent-status-direct-slash"),
    path(
        "internal/<str:user_id>/eligibility",
        InternalEligibilityView.as_view(),
        name="internal-eligibility",
    ),
    path(
        "internal/<str:user_id>/eligibility/",
        InternalEligibilityView.as_view(),
        name="internal-eligibility-slash",
    ),
    path("students/", include("apps.students.urls")),
    path("companies/", include("apps.companies.urls")),
]
