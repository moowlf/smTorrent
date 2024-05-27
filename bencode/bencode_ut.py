import unittest
import bencode


class BencodeTest(unittest.TestCase):

    def test_encode_integer(self):
        encoded_data = bencode.encode_integer(42)
        self.assertEqual(encoded_data, b"i42e")

    def test_decode_integer(self):
        decoded_data, sz = bencode.decode_integer(b"i42e")
        self.assertEqual(decoded_data, 42)
        self.assertEqual(sz, 4)

    def test_encode_string(self):
        encoded_data = bencode.encode_string("spam")
        self.assertEqual(encoded_data, b"4:spam")

    def test_decode_string(self):
        decoded_data, sz = bencode.decode_string(b"4:spam")
        self.assertEqual(decoded_data, b"spam")
        self.assertEqual(sz, 6)

    def test_decode_list(self):
        decoded_data, sz = bencode.decode_list(b"l4:spami42ee")
        self.assertEqual(decoded_data, [b"spam", 42])
        self.assertEqual(sz, 12)

    def test_encode_list(self):
        encoded = bencode.encode_list([42, "spam", ["moowlf"]])
        self.assertEqual(encoded, b"li42e4:spaml6:moowlfee")

    def test_empty_dictionary(self):
        with self.assertRaises(bencode.BencodeException) as cm:
            bencode.decode_dictionary(b"")
        self.assertEqual(str(cm.exception), "Decoding empty dictionary is undefined behaviour")

    def test_simple_dictionary(self):
        decoded_dict, _ = bencode.decode_dictionary(b"d4:name5:Alice3:agei42ee")
        self.assertEqual(decoded_dict, {"name": b"Alice", "age": 42})

    def test_nested_dictionary(self):
        decoded_dict, _ = bencode.decode_dictionary(b"d4:infod4:name10:MyFile.txt6:lengthi1000ee4:useri10ee")
        self.assertEqual(decoded_dict, {
            "info": {
                "name": b"MyFile.txt",
                "length": 1000
            },
            "user": 10
        })

    def test_invalid_key(self):
        with self.assertRaises(bencode.BencodeException) as cm:
            bencode.decode_dictionary(b"d1:keyi10e")  # Key must be a string

    def test_encode_decode_roundtrip(self):
        data = {"name": "Bob", "age": 30, "info": {"files": ["file1.txt", "file2.jpg"]}}
        encoded_data = bencode.encode_dictionary(data)
        decoded_dict, _ = bencode.decode_dictionary(encoded_data)
        self.assertEqual(data, decoded_dict)

    def test_encode_empty_string(self):
        encoded_data = bencode.encode_string("")
        self.assertEqual(encoded_data, b"0:")

    def test_decode_empty_string(self):
        decoded_data, sz = bencode.decode_string(b"0:")
        self.assertEqual(decoded_data, b"")
        self.assertEqual(sz, 2)

    def test_decode_invalid_integer_format(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_integer(b"invalid")

    def test_decode_invalid_integer_value(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_integer(b"iabcde")

    def test_decode_string_missing_colon(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_string(b"invalid format")

    def test_decode_string_negative_size(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_string(b"-1:data")

    def test_decode_string_invalid_size(self):
        with self.assertRaises(bencode.BencodeException):
            bencode.decode_string(b"abc:data")


# Add tests for decode_list functionality once implemented

if __name__ == "__main__":
    unittest.main()
