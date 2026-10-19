from rest_framework.routers import DefaultRouter
from .views import (
    ChargingStationViewSet,
    ChargerViewSet,
    TariffPeriodViewSet,
    ChargingSessionViewSet,
)

router = DefaultRouter()
router.register(r"stations", ChargingStationViewSet, basename="charging-station")
router.register(r"chargers", ChargerViewSet, basename="charger")
router.register(r"tariffs", TariffPeriodViewSet, basename="tariff")
router.register(r"sessions", ChargingSessionViewSet, basename="charging-session")

urlpatterns = router.urls