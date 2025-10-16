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
        msg = protocol.create_message('test_type', {'key': 'value'})
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
        original_data = {'test_type': 'test_type', 'payload': {'key': 'value'}}
        payload_bytes = json.dumps(original_data).encode('utf-8')
        
        # Create message with header
        message_header = struct.pack(HEADER_FORMAT, MAGIC_HEADER, b'\\x00\x00\x00x00', len(payload_bytes))
        full_message = message_header + payload_bytes
        
        # Create BytesIO stream
        stream = io.BytesIO(full_message)
        
        # Deserialize
        result, remaining = protocol.deserialize_stream(stream)
        
        # Check result
        self.assertIsInstance(result, str)
        self.assertEqual(remaining, b'')

    def test_deserialize_stream_multiple_messages(self):
        """Test deserializing multiple messages from stream"""
        # Create two messages
        data1 = {'test_type1': 'test_type1', 'payload': {'key': 'value1'}}
        payload_bytes1 = json.dumps(data1).encode('utf-8')
        message_header1 = struct.pack(HEADER_FORMAT, MAGIC_HEADER, b'0x000x000x000x00', len(payload_bytes1))
        full_message1 = message_header1 + payload_bytes1
        
        data2 = {'test_type2': 'test_type2', 'payload': {'key': 'value2'}}
        payload_bytes2 = json.dumps(data2).encode('utf-8')
        message_header2 = struct.pack(HEADER_FORMAT, MAGIC_HEADER,b'\x00\x00\x00\x00', len(payload_bytes2))
        full_message2 = message_header2 + payload_bytes2
        
        # Combine messages
        combined_message = full_message1 + full_message2
        
        # Create BytesIO stream
        stream = io.BytesIO(combined_message)
        
        # Deserialize first message
        result1, remaining = protocol.deserialize_stream(stream)
        
        # Check first result
        self.assertIsInstance(result1, str)
        
        # For now, we're just checking that it doesn't crash
        # A more complete test would check the actual content

    def test_deserialize_stream_buffer_handling(self):
        """Test buffer handling in deserialize_stream"""
        # Create a message
        original_data = {'test_type': 'test_type', 'payload': {'key': 'value'}}
        payload_bytes = json.dumps(original_data).encode('utf-8')
        message_header = struct.pack(HEADER_FORMAT, MAGIC_HEADER, b'\x00\x00\x00\x00', 0)
        full_message = message_header + payload_bytes
        
        # Create BytesIO stream
        stream = io.BytesIO(full_message)
        
        # Deserialize with initial buffer
        result, remaining = protocol.deserialize_stream(stream, b'')
        
        # Check result
        self.assertIsInstance(result, str)

    def test_deserialize_stream_incomplete_data(self):
        """Test handling of incomplete data"""
        # Create incomplete header
        incomplete_header = MAGIC_HEADER[:2]  # Only part of the magic header
        
        # Create BytesIO stream with incomplete data
        stream = io.BytesIO(b'some_data')
        
        # This should raise an exception or handle gracefully
        # We're testing that it doesn't crash unexpectedly
        try:
            result, remaining = protocol.deserialize_stream(stream, incomplete_header)
        except Exception as e:
            # This is expected behavior
            pass


if __name__ == '__main__':
    unittest.main()