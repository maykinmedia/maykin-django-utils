from django.urls import path

from health_check.views import HealthCheckView

# Default/convention for URL patterns. With all the defaults, this makes the following
# URLs available:
#
# * ``/_healthz/`` -> reports on all health checks configured
# * ``/_healthz/livez/`` -> no plugins at all, simple check if the app is alive
# * ``/_healthz/readyz/`` -> essential plugins, check if the app can do useful work
urlpatterns = [
    path(
        "_healthz/",
        HealthCheckView.as_view(
            checks=[
                ("health_check.Cache", {"alias": "default"}),
                ("health_check.Database", {"alias": "default"}),
                ("health_check.Storage", {"alias": "default"}),
            ]
        ),
    ),  # all reliable checks
    path("_healthz/livez/", HealthCheckView.as_view(checks=[])),  # no checks
    path(
        "_healthz/readyz/",
        HealthCheckView.as_view(
            checks=[
                ("health_check.Cache", {"alias": "default"}),
                ("health_check.Database", {"alias": "default"}),
            ]
        ),
    ),
]
