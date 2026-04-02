import logging

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger('newshub.health')


class BaseHealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class HealthCheckView(BaseHealthCheckView):
    def get(self, _request):
        return Response(
            {
                'status': 'ok',
                'service': 'newshub-backend',
                'environment': settings.APP_ENV,
                'timestamp': timezone.now().isoformat(),
            }
        )


class DatabaseHealthCheckView(BaseHealthCheckView):
    def get(self, _request):
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            return Response({'status': 'ok', 'database': 'available'})
        except OperationalError as exc:
            logger.warning('Database health check failed: %s', exc)
            return Response(
                {'status': 'error', 'database': 'unavailable', 'detail': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class RedisHealthCheckView(BaseHealthCheckView):
    def get(self, _request):
        try:
            connection = get_redis_connection('default')
            connection.ping()
            return Response({'status': 'ok', 'redis': 'available'})
        except Exception as exc:  # noqa: BLE001
            logger.warning('Redis health check failed: %s', exc)
            return Response(
                {'status': 'error', 'redis': 'unavailable', 'detail': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
