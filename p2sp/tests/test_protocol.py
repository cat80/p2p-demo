import unittest
import io
import json
import struct
from p2sp.protocol import protocol, MAGIC_HEADER, HEADER_FORMAT, HEADER_LEN


class TestProtocol(unittest.TestCase):

    def test_constants(self):
        """Test protocol constants"""
        self.assertEqual(MAGIC_HEADER, b'\xab\xcd\xef\x88')
        self.assertEqual(HEADER_FORMAT, '<4s4sI')
        self.assertEqual(HEADER_LEN, 12)  # 4 bytes for magic header + 4 bytes for payload len + 4 bytes for checksum

    def test_create_ping(self):
        """Test creating ping message"""
        ping_msg = protocol.create_ping()
        self.assertIsInstance(ping_msg, bytes)
        self.assertTrue(ping_msg.startswith(MAGIC_HEADER))

    def test_create_pong(self):
        """Test creating pong message"""
        pong_msg = protocol.create_pong()
        self.assertIsInstance(pong_msg, bytes)
        self.assertTrue(pong_msg.startswith(MAGIC_HEADER))

    def test_create_message(self):
        """Test creating generic message"""
        msg = protocol.create_payload('test_type', {'key': 'value'})
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

    def test_serialize_message(self):
        """Test serializing message"""
        # Test with payload
        msg = protocol.serialize_message('test_type', {'key': 'value'})
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Test without payload
        msg = protocol.serialize_message('test_type')
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

    def test_deserialize_stream_simple(self):
        """Test deserializing simple message from stream"""
        # Create a simple message
        original_data = {'type': 'test_type', 'payload': {'key': 'value'}, 'timestamp': 1234567890}
        payload_bytes = json.dumps(original_data).encode('utf-8')

        # Create message with header
        message_header = struct.pack(HEADER_FORMAT, MAGIC_HEADER, b'\x00\x00\x00\x00', len(payload_bytes))
        full_message = message_header + payload_bytes

        # Create BytesIO stream
        stream = io.BytesIO(full_message)

        # Deserialize
        result, remaining = protocol.deserialize_stream(stream)

        # Check result
        self.assertIsInstance(result, dict)
        self.assertEqual(remaining, b'')

    def test_deserialize_stream_multiple_messages(self):
        """Test deserializing multiple messages from stream"""
        # Create two messages
        data1 = {'type': 'test_type1', 'payload': {'key': 'value1'}, 'timestamp': 1234567890}
        payload_bytes1 = json.dumps(data1).encode('utf-8')
        message_header1 = struct.pack(HEADER_FORMAT, MAGIC_HEADER, b'\x00\x00\x00\x00', len(payload_bytes1))
        full_message1 = message_header1 + payload_bytes1

        data2 = {'type': 'test_type2', 'payload': {'key': 'value2'}, 'timestamp': 1234567891}
        payload_bytes2 = json.dumps(data2).encode('utf-8')
        message_header2 = struct.pack(HEADER_FORMAT, MAGIC_HEADER, b'\x00\x00\x00\x00', len(payload_bytes2))
        full_message2 = message_header2 + payload_bytes2

        # Combine messages
        combined_message = full_message1 + full_message2

        # Create BytesIO stream
        stream = io.BytesIO(combined_message)

        # Deserialize first message
        result1, remaining1 = protocol.deserialize_stream(stream)

        # Check first result
        self.assertIsInstance(result1, dict)
        self.assertEqual(result1['type'], 'test_type1')

        # Deserialize second message
        result2, remaining2 = protocol.deserialize_stream(stream, remaining1)
        self.assertIsInstance(result2, dict)
        self.assertEqual(result2['type'], 'test_type2')
        self.assertEqual(remaining2, b'')

    def test_deserialize_stream_buffer_handling(self):
        """Test buffer handling in deserialize_stream"""
        # Create a message
        original_data = {'type': 'test_type', 'payload': {'key': 'value'}, 'timestamp': 1234567890}
        payload_bytes = json.dumps(original_data).encode('utf-8')
        message_header = struct.pack(HEADER_FORMAT, MAGIC_HEADER, b'\x00\x00\x00\x00', len(payload_bytes))
        full_message = message_header + payload_bytes

        # Create BytesIO stream
        stream = io.BytesIO(full_message)

        # Deserialize with initial buffer
        result, remaining = protocol.deserialize_stream(stream, b'')

        # Check result
        self.assertIsInstance(result, dict)

    def test_deserialize_stream_incomplete_data(self):
        """Test handling of incomplete data"""
        # Create incomplete header
        incomplete_header = MAGIC_HEADER[:2]  # Only part of the magic header

        # Create BytesIO stream with incomplete data
        stream = io.BytesIO(b'some_data')

        # This should raise an exception or handle gracefully
        with self.assertRaises(Exception):
            result, remaining = protocol.deserialize_stream(stream, incomplete_header)

    def test_create_normal_message(self):
        """Test creating normal message"""
        msg = protocol.create_normal_message("Hello World")
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Deserialize to check content
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertEqual(result['type'], 'normalmsg')
        self.assertEqual(result['payload']['message'], 'Hello World')

    def test_create_signal_message(self):
        """Test creating signal message"""
        msg = protocol.create_user_send_message("user1", "Hello user1")
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Deserialize to check content
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertEqual(result['type'], 'send')
        self.assertEqual(result['payload']['touser'], 'user1')
        self.assertEqual(result['payload']['message'], 'Hello user1')

    def test_create_broadcast_message(self):
        """Test creating broadcast message"""
        msg = protocol.create_broadcast_message("Broadcast message")
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Deserialize to check content
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertEqual(result['type'], 'broadcast')
        self.assertEqual(result['payload']['message'], 'Broadcast message')

    def test_create_reg_message(self):
        """Test creating registration message"""
        msg = protocol.create_reg_message("testuser")
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Deserialize to check content
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertEqual(result['type'], 'reg')
        self.assertEqual(result['payload']['username'], 'testuser')

    def test_create_sys_notify(self):
        """Test creating system notification"""
        msg = protocol.create_sys_notify("System notification")
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Deserialize to check content
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertEqual(result['type'], 'sysmsg')
        self.assertEqual(result['payload']['message'], 'System notification')

    def test_create_user_send_message(self):
        """Test creating user send message"""
        msg = protocol.create_user_send_message("sender", "Private message")
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Deserialize to check content
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertEqual(result['type'], 'usersend')
        self.assertEqual(result['payload']['fromusername'], 'sender')
        self.assertEqual(result['payload']['message'], 'Private message')

    def test_create_user_broadcast_message(self):
        """Test creating user broadcast message"""
        msg = protocol.create_user_broadcast_message("sender", "Public message")
        self.assertIsInstance(msg, bytes)
        self.assertTrue(msg.startswith(MAGIC_HEADER))

        # Deserialize to check content
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertEqual(result['type'], 'userbroadcast')
        self.assertEqual(result['payload']['fromusername'], 'sender')
        self.assertEqual(result['payload']['message'], 'Public message')

    def test_show_user_msg_sysmsg(self):
        """Test showing system message"""
        payload = {
            'type': 'sysmsg',
            'payload': {'message': 'Welcome!'},
            'timestamp': 1234567890
        }
        result = protocol.show_user_msg(payload)
        self.assertIn('[系统消息]:Welcome!', result)

    def test_show_user_msg_usersend(self):
        """Test showing user send message"""
        payload = {
            'type': 'usersend',
            'payload': {
                'fromusername': 'sender',
                'message': 'Hello!'
            },
            'timestamp': 1234567890
        }
        result = protocol.show_user_msg(payload)
        print(result)
        self.assertIn('sender悄悄对你说:Hello!', result)

    def test_show_user_msg_userbroadcast(self):
        """Test showing user broadcast message"""
        payload = {
            'type': 'userbroadcast',
            'payload': {
                'fromusername': 'sender',
                'message': 'Hello everyone!'
            },
            'timestamp': 1234567890
        }
        result = protocol.show_user_msg(payload)
        self.assertIn('sender:Hello everyone!', result)

    def test_show_user_msg_invalid_payload(self):
        """Test showing user message with invalid payload"""
        # Test with non-dict payload
        result = protocol.show_user_msg("invalid")
        self.assertIn('消息不能为空，且消息必须为dict', result)

        # Test with dict without type
        result = protocol.show_user_msg({'payload': {}})
        self.assertIn('未知的消息类型', result)

    def test_timestamp_in_messages(self):
        """Test that messages contain timestamps"""
        msg = protocol.create_ping()
        stream = io.BytesIO(msg)
        result, _ = protocol.deserialize_stream(stream)
        self.assertIn('timestamp', result)
        self.assertIsInstance(result['timestamp'], int)


if __name__ == '__main__':
    unittest.main()
