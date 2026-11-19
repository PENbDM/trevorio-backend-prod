import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE','trevorio.settings')

app = Celery('trevorio')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(10.0, test.s('hello1'), name='add every 10')
#
#     sender.add_periodic_task(30.0,test.s('hello2'), name='add every 30')
#
#     sender.add_periodic_task(30.0,test.s('world3'), expires=10)
#
#     sender.add_periodic_task(
#         crontab(hour=7, minute=30, day_of_week=1),
#         test.s('happy monday4'),
#     )
#
# @app.task
# def test(arg):
#     print(arg)
#
# @app.task
# def add(x, y):
#     z=x+y
#     print(z)
