from celery import shared_task
from .services.change_detector import change_detector
@shared_task
def change_detector_worker():
    change_detector()
