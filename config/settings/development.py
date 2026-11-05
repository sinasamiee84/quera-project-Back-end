from .base import *  # noqa: F403

# COURSE_TODO: enable development mode and local hosts.
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1','testserver']
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CELERY_TASK_ALWAYS_EAGER = True