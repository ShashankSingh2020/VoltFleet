from rest_framework.routers import DefaultRouter
from .views import AnomalyViewSet

router = DefaultRouter()
router.register(r"", AnomalyViewSet, basename="anomaly")

urlpatterns = router.urls