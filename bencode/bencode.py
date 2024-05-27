class BencodeException(Exception):
    pass


def _decode_numeric_form(data: bytes, position=0):
    beginning = position
    value = 0

    is_negative = False
    if position < len(data) and _read_byte(data, position) == '-':
        is_negative = True
        position += 1

    while position < len(data) and _read_byte(data, position).isdigit():
        value = value * 10 + int(_read_byte(data, position))
        position += 1

    if is_negative:
        value *= -1

    return value, position - beginning


def _read_byte(data, position):
    return chr(data[position])


def decode_integer(data: bytes, position=0):
    """
    Decodes a string into an integer. Bencode encodes an integer as i<number>e
    :param data: An integer in bencode mode
    :param position: The position in which the parser should start
    :return: A tuple of an integer in its decimal form and the amount of characters read
    """
    if len(data) == 0:
        raise BencodeException("Decoding empty integer is undefined behaviour.")

    if position > len(data):
        raise BencodeException("Decoding pos word has no meaning.")

    if _read_byte(data, position) != 'i':
        raise BencodeException("Decoding integer with invalid format for integers.")

    # Consume the 'i'
    beginning = position
    position += 1

    integer, parsed_size = _decode_numeric_form(data, position)
    position += parsed_size

    if _read_byte(data, position) != 'e':
        raise BencodeException(f"Couldn't find the end terminator in the string")

    position += 1  # consume the end "e"

    return integer, position - beginning


def encode_integer(data: int):
    """
    Encodes an integer into its bencoded form. Bencode encodes as i<number>e
    :param data: An integer in its decimal form
    :return: Bencoded Integer
    """
    return str.encode('i' + str(data) + 'e')


def decode_string(data: bytes, position=0):
    """
    Decodes a bencoded formatted string into its python form. Bencode algorithm encodes a string as <size>:data
    :param data: A bencoded formatted string
    :param position: The position in which the parser should start
    :return: A tuple of a string in its pythonic form and the amount of chars read
    """

    beginning = position

    # Read the first part of the schema
    strlen, read_chars = _decode_numeric_form(data, position)
    position += read_chars
    if _read_byte(data, position) != ":":
        raise BencodeException("Missing colon makes it impossible to determine the size of the string.")

    if strlen < 0:
        raise BencodeException(f"Bencode format does not allow numbers inferior to zero as length.")

    position += 1
    return data[position:position + strlen], position + strlen - beginning


def encode_string(string: str):
    """
    Converts a string in its "normal" form to a bencoded format
    :param string: A valid string in its common representation
    :return: A bencoded formatted string
    """
    value = str(len(string)) + ':' + string
    return str.encode(value)


def decode_list(data: bytes, position=0):
    """
    Decodes a string formatted list into its pythonic representation
    :param data: A list encoded as a string
    :param position: Initial position to start the parse
    :return: A pythonic representation of the list passed as argument
    """

    if len(data) == 0:
        raise BencodeException("Decoding empty integer is undefined behaviour")

    if _read_byte(data, position) != 'l':
        raise BencodeException("Decoding integer with invalid format for lists.")

    beginning = position
    position += 1  # consume the l

    arr = []

    while position < len(data):

        if _read_byte(data, position) == "e":
            break

        if _read_byte(data, position) == "i":
            integer, read_chars = decode_integer(data, position)
            arr.append(integer)
            position += read_chars

        elif _read_byte(data, position).isdigit():
            string, read_chars = decode_string(data, position)
            arr.append(string)
            position += read_chars

        elif _read_byte(data, position) == "l":
            lst, read_chars = decode_list(data, position)
            arr.append(lst)
            position += read_chars

        elif _read_byte(data, position) == "d":
            d, read_chars = decode_dictionary(data, position)
            arr.append(d)
            position += read_chars

    if position >= len(data) or _read_byte(data, position) != "e":
        raise BencodeException(f"Decoding list failed. Current list so far {arr}")

    position += 1  # Consume last "e"

    return arr, position - beginning


def encode_list(lst):
    """
    Encodes a pythonic list to a string in bencode format
    :param lst: The list to be encoded
    :return: A String representing the passed list in bencode format
    """
    #data = bytearray()
    data = b'l'

    for obj in lst:
        if type(obj) is int:
            data += encode_integer(obj)
        elif type(obj) is list:
            data += encode_list(obj)
        elif type(obj) is str:
            data += encode_string(obj)
        elif type(obj) is dict:
            data += encode_dictionary(obj)

    data += b'e'
    return data


def decode_dictionary(data: bytes, position=0):
    if len(data) == 0:
        raise BencodeException("Decoding empty dictionary is undefined behaviour")

    if _read_byte(data, position) != 'd':
        raise BencodeException("Decoding integer with invalid format for lists.")

    beginning = position
    position += 1  # consume the d
    dic = {}

    while position < len(data):

        read_byte = _read_byte(data, position)

        if read_byte == "e":
            break

        #if not (_read_byte(data, position).isdigit()):
        #    raise BencodeException("All keys in a dictionary must be strings")

        key, read_chars = decode_string(data, position)
        position += read_chars

        if _read_byte(data, position) == "i":
            integer, read_chars = decode_integer(data, position)
            dic[key.decode()] = integer
            position += read_chars

        elif _read_byte(data, position).isdigit():
            string, read_chars = decode_string(data, position)
            dic[key.decode()] = string
            position += read_chars

        elif _read_byte(data, position) == "l":
            lst, read_chars = decode_list(data, position)
            dic[key.decode()] = lst
            position += read_chars

        elif _read_byte(data, position) == "d":
            d, read_chars = decode_dictionary(data, position)
            dic[key.decode()] = d
            position += read_chars

        else:
            raise BencodeException(f"Decoding dictionary failed. Current list so far {dic}")

    if position >= len(data) or _read_byte(data, position) != "e":
        raise BencodeException(f"Decoding dictionary failed. Current list so far {dic}")

    position += 1  # Consume last "e"

    return dic, position - beginning


def encode_dictionary(dictionary):
    """
    Encodes a pythonic object to a string in bencode format
    :param dictionary: The dictionary to be encoded
    :return: A String representing the passed dictionary in bencode format
    """
    data = bytearray()
    data += b'd'

    for obj in dictionary:

        data += encode_string(obj)

        if type(dictionary[obj]) is int:
            data += encode_integer(dictionary[obj])
        elif type(dictionary[obj]) is list:
            data += encode_list(dictionary[obj])
        elif type(dictionary[obj]) is str:
            data += encode_string(dictionary[obj])
        elif type(dictionary[obj]) is dict:
            data += encode_dictionary(dictionary[obj])
        elif type(dictionary[obj]) is bytes:
            res = bytearray()
            res += str.encode(str(len(dictionary[obj])))
            res += b':'
            res += dictionary[obj]
            data += res
        else:
            raise 'yelp'
    data += b'e'
    return data
