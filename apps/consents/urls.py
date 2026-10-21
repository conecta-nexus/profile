from django.urls import path

from apps.consents.views import ConsentRegistrationView, ConsentStatusView

app_name = "consents"

urlpatterns = [
    path("", ConsentRegistrationView.as_view(), name="consent-register"),
    path("me", ConsentStatusView.as_view(), name="consent-status"),
    path("me/", ConsentStatusView.as_view(), name="consent-status-slash"),
]
