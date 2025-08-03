
import unittest
from unittest.mock import patch, MagicMock
import meross_iot_rest
from meross_iot_rest import app

class MerossIotRestTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        meross_iot_rest.meross_initialized = True

    def tearDown(self):
        pass

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'Hello to MerossIOT REST!')

    def test_healthcheck_ok(self):
        response = self.client.get('/healthcheck')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'OK', response.data)

    def test_healthcheck_not_ok(self):
        meross_iot_rest.meross_initialized = False
        response = self.client.get('/healthcheck')
        self.assertEqual(response.status_code, 500)
        self.assertIn(b'Meross loop not initialised', response.data)

    def test_sockets_operation_on(self):
        with patch('meross_iot_rest.device_operations_queue') as mock_queue:
            response = self.client.get('/sockets/on/1')
            self.assertEqual(response.status_code, 202)
            mock_queue.put.assert_called_with(('on', 1))

    def test_sockets_operation_off(self):
        with patch('meross_iot_rest.device_operations_queue') as mock_queue:
            response = self.client.get('/sockets/off/2')
            self.assertEqual(response.status_code, 202)
            mock_queue.put.assert_called_with(('off', 2))

    def test_sockets_operation_toggle(self):
        with patch('meross_iot_rest.device_operations_queue') as mock_queue:
            response = self.client.get('/sockets/toggle/0')
            self.assertEqual(response.status_code, 202)
            mock_queue.put.assert_called_with(('toggle', 0))

    def test_sockets_operation_invalid_operation(self):
        response = self.client.get('/sockets/invalid_op/1')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Invalid operation', response.data)

    def test_sockets_operation_invalid_socket_no_str(self):
        response = self.client.get('/sockets/on/abc')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Invalid socket number', response.data)
        
    def test_sockets_operation_invalid_socket_no_out_of_bounds(self):
        response = self.client.get('/sockets/on/3')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Socket number out of bounds', response.data)

if __name__ == '__main__':
    unittest.main()
