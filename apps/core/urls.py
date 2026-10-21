from django.urls import include, path

urlpatterns = [
    path("consent", include("apps.consents.urls")),
    path("consent/", include("apps.consents.urls")),
    path("consents/", include("apps.consents.urls")),
    path("students/", include("apps.students.urls")),
    path("companies/", include("apps.companies.urls")),
]
