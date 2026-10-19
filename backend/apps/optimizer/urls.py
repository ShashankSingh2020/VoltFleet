from rest_framework.routers import DefaultRouter
from .views import ChargingPlanViewSet

router = DefaultRouter()
router.register(r"plans", ChargingPlanViewSet, basename="charging-plan")

urlpatterns = router.urls