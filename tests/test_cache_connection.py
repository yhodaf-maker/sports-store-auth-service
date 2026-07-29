import sys
import unittest
from unittest.mock import MagicMock, patch


class TestCacheConnection(unittest.TestCase):
    def setUp(self):
        # Clear module cache so imports reload config
        if 'cache' in sys.modules:
            del sys.modules['cache']

    def tearDown(self):
        if 'cache' in sys.modules:
            del sys.modules['cache']

    @patch('redis.sentinel.Sentinel')
    @patch.dict('os.environ', {
        'REDIS_SENTINELS': 'sentinel-service:26379',
        'REDIS_PASSWORD': 'testpassword',
        'REDIS_MASTER_NAME': 'mymaster'
    })
    def test_sentinel_initialization(self, mock_sentinel):
        mock_sentinel_instance = MagicMock()
        mock_sentinel.return_value = mock_sentinel_instance
        
        import cache
        
        mock_sentinel.assert_called_once_with(
            [('sentinel-service', 26379)],
            socket_timeout=0.2,
            password='testpassword'
        )
        
        mock_sentinel_instance.master_for.assert_called_once_with(
            'mymaster',
            socket_timeout=0.2,
            password='testpassword'
        )
        self.assertEqual(cache.redis_client, mock_sentinel_instance.master_for.return_value)

    @patch('redis.Redis')
    @patch.dict('os.environ', {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': 'fallbackpassword'
    })
    def test_standalone_fallback(self, mock_redis):
        with patch.dict('os.environ', {'REDIS_SENTINELS': ''}):
            import cache
            mock_redis.assert_called_once_with(
                host='localhost',
                port=6379,
                password='fallbackpassword',
                socket_timeout=0.2
            )
            self.assertEqual(cache.redis_client, mock_redis.return_value)
