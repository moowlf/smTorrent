import unittest
from bencode import bencode


class BencodeTest(unittest.TestCase):

    def test_encode_integer(self):
        data = 42
        encoded_data = bencode.encode_integer(42)
        self.assertEqual(encoded_data, "i42e")

    def test_decode_integer(self):
        data = "i42e"
        decoded_data = bencode.decode_integer(data)
        self.assertEqual(decoded_data, 42)

    def test_encode_string(self):
        data = "spam"
        encoded_data = bencode.encode_string(data)
        self.assertEqual(encoded_data, b"4:spam")

    def test_decode_string(self):
        data = b"4:spam"
        decoded_data = bencode.decode_string(data.decode())  # decode bytes to string for testing
        self.assertEqual(decoded_data, "spam")

    def test_encode_empty_string(self):
        data = ""
        encoded_data = bencode.encode_string(data)
        self.assertEqual(encoded_data, b"0:")

    def test_decode_empty_string(self):
        data = b"0:"
        decoded_data = bencode.decode_string(data.decode())  # decode bytes to string for testing
        self.assertEqual(decoded_data, "")

    def test_encode_negative_integer_raises_exception(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.encode_integer(-1)

    def test_decode_invalid_integer_format(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_integer("invalid")

    def test_decode_invalid_integer_value(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_integer("iabcde")

    def test_decode_string_missing_colon(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_string("invalid format")

    def test_decode_string_negative_size(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_string("-1:data")

    def test_decode_string_invalid_size(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_string("abc:data")


# Add tests for decode_list functionality once implemented

if __name__ == "__main__":
    unittest.main()
