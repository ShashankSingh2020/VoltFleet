from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def health_check(request):
    return JsonResponse(
        {
            "status": "healthy",
            "service": "VoltFleet Intelligence Engine",
            "version": "1.0.0"
        },
        status=200
    )

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/", include("apps.vehicles.urls")),
    path("api/v1/telemetry/", include("apps.telemetry.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/charging/", include("apps.charging.urls")),
    path("api/v1/optimizer/", include("apps.optimizer.urls")),
    path("api/v1/anomalies/", include("apps.anomalies.urls")),
    path("api/v1/ai/", include("apps.ai_assistant.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]