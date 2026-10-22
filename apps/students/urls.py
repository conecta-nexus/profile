from django.urls import path

from apps.students.views import StudentProfileMeView, StudentProfilePublicView

app_name = "students"

urlpatterns = [
    path("me", StudentProfileMeView.as_view(), name="profile-me"),
    path(
        "<uuid:user_id>/public",
        StudentProfilePublicView.as_view(),
        name="profile-public",
    ),
]
