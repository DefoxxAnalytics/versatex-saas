"""Tests for /api/health/ readiness endpoint."""
from unittest.mock import patch

import pytest
from django.test import Client


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_returns_200_when_all_healthy(self):
        response = Client().get('/api/health/')
        assert response.status_code == 200
        assert response.json() == {'db': 'ok', 'redis': 'ok'}

    def test_returns_503_when_db_fails(self):
        with patch('apps.health.views.connection') as mock_conn:
            mock_conn.cursor.side_effect = Exception('db down')
            response = Client().get('/api/health/')
        assert response.status_code == 503
        assert response.json() == {'db': 'error', 'redis': 'ok'}

    def test_returns_503_when_cache_fails(self):
        with patch('apps.health.views.cache') as mock_cache:
            mock_cache.set.side_effect = Exception('redis down')
            response = Client().get('/api/health/')
        assert response.status_code == 503
        assert response.json() == {'db': 'ok', 'redis': 'error'}

    def test_returns_503_when_both_fail(self):
        with patch('apps.health.views.connection') as mock_conn, \
             patch('apps.health.views.cache') as mock_cache:
            mock_conn.cursor.side_effect = Exception('db down')
            mock_cache.set.side_effect = Exception('redis down')
            response = Client().get('/api/health/')
        assert response.status_code == 503
        assert response.json() == {'db': 'error', 'redis': 'error'}

    def test_returns_503_when_cache_readback_mismatches(self):
        with patch('apps.health.views.cache') as mock_cache:
            mock_cache.set.return_value = None
            mock_cache.get.return_value = 'wrong-value'
            response = Client().get('/api/health/')
        assert response.status_code == 503
        assert response.json() == {'db': 'ok', 'redis': 'error'}

    def test_rejects_post(self):
        response = Client().post('/api/health/')
        assert response.status_code == 405

    def test_no_auth_required(self):
        # Health probe must work from unauth contexts (Kuma, CF tunnel).
        response = Client().get('/api/health/')
        assert response.status_code == 200

    def test_sets_no_cache_headers(self):
        response = Client().get('/api/health/')
        assert 'no-cache' in response.headers.get('Cache-Control', '').lower() or \
               'no-store' in response.headers.get('Cache-Control', '').lower() or \
               'max-age=0' in response.headers.get('Cache-Control', '').lower()
