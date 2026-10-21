from django.urls import path

from apps.companies.views import CompanyProfileMeView, CompanyProfilePublicView

app_name = "companies"

urlpatterns = [
    path("me", CompanyProfileMeView.as_view(), name="profile-me"),
    path(
        "<uuid:user_id>/public",
        CompanyProfilePublicView.as_view(),
        name="profile-public",
    ),
]
