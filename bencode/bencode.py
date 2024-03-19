from bencode.exceptions import BencodeException


def decode_integer(data: str):
    """
    Decodes a string into an integer. Bencode encodes an integer as i<number>e
    :param data: An integer in bencode mode
    :return: An integer in its decimal form
    """
    if len(data) == 0:
        raise BencodeException("Decoding empty integer is undefined behaviour")

    if data[0] != 'i' or data[-1] != 'e':
        raise BencodeException("Decoding integer with invalid format for integers.")

    try:
        result = int(data[1:-1])
    except Exception as e:
        raise BencodeException(f"Tried to convert an invalid integer: {data[1:-1]}")

    return result


def encode_integer(data: int):
    """
    Encodes an integer into its bencoded form. Bencode encodes as i<number>e
    :param data: An integer in its decimal form
    :return: Bencoded Integer
    """
    return 'i' + str(data) + 'e'


def decode_string(data: str):
    """
    Decodes a bencoded formatted string into its python form. Bencode algorithm encodes a string as <size>:data
    :param data: A bencoded formatted string
    :return: A string in its pythonic form
    """
    separator = data.find(':')

    if separator == -1:
        raise BencodeException("Missing colon makes it impossible to determine the size of the string.")

    try:
        string_size = int(data[:separator])
    except Exception as e:
        raise BencodeException(f"Something went wrong while parsing the size of the string: {data[:separator]}")

    if string_size < 0:
        raise BencodeException(f"Bencode format does not allow numbers inferior to zero as length.")

    beginning = separator + 1
    return data[beginning:beginning + string_size]


def encode_string(string: str):
    """
    Converts a string in its "normal" form to a bencoded format
    :param string: A valid string in its common representation
    :return: A bencoded formatted string
    """
    return str(len(string)) + ":" + string
