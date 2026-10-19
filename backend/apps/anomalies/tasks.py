from celery import shared_task
from apps.authentication.models import Organization
from apps.anomalies.detector import AnomalyDetectionEngine


@shared_task(name="apps.anomalies.tasks.run_scheduled_anomaly_scans")
def run_scheduled_anomaly_scans():
    """
    Periodic job triggered by Celery Beat to scan active fleets for critical thresholds.
    """
    active_orgs = Organization.objects.filter(is_active=True)
    total_detected = 0

    for org in active_orgs:
        new_anomalies = AnomalyDetectionEngine.scan_organization(org)
        total_detected += len(new_anomalies)

    return {
        "status": "completed",
        "organizations_scanned": active_orgs.count(),
        "new_anomalies_detected": total_detected
    }