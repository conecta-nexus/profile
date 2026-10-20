from django.urls import include, path

urlpatterns = [
    path("consents/", include("apps.consents.urls")),
    path("students/", include("apps.students.urls")),
    path("companies/", include("apps.companies.urls")),
]