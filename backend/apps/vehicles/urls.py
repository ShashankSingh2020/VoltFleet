from rest_framework.routers import DefaultRouter
from .views import FleetViewSet, VehicleSpecificationViewSet, VehicleViewSet

router = DefaultRouter()
router.register(r"fleets", FleetViewSet, basename="fleet")
router.register(r"specifications", VehicleSpecificationViewSet, basename="specification")
router.register(r"vehicles", VehicleViewSet, basename="vehicle")

urlpatterns = router.urls