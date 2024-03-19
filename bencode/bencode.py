class BencodeException(Exception):
    pass


def decode_numeric_form(data: str, position = 0):


def decode_integer(data: str, position=0):
    """
    Decodes a string into an integer. Bencode encodes an integer as i<number>e
    :param data: An integer in bencode mode
    :param position: The position in which the parser should start
    :return: An integer in its decimal form
    """
    if len(data) == 0:
        raise BencodeException("Decoding empty integer is undefined behaviour.")

    if position > len(data):
        raise BencodeException("Decoding pos word has no meaning.")

    if data[position] != 'i':
        raise BencodeException("Decoding integer with invalid format for integers.")

    # Consume the 'i'
    beginning = position
    position += 1

    result = 0
    valid = False
    while position < len(data):

        if data[position] == 'e':
            valid = True
            position += 1
            break

        elif "0" <= data[position] <= "9":
            result = result * 10 + int(data[position])
            position += 1

        else:
            raise BencodeException(f"Tried to convert an character in integer: {data}")

    if not valid:
        raise BencodeException(f"Couldn't find the end terminator in the string")

    return result, position - beginning + 1


def encode_integer(data: int):
    """
    Encodes an integer into its bencoded form. Bencode encodes as i<number>e
    :param data: An integer in its decimal form
    :return: Bencoded Integer
    """
    return 'i' + str(data) + 'e'


def decode_string(data: str, position = 0):
    """
    Decodes a bencoded formatted string into its python form. Bencode algorithm encodes a string as <size>:data
    :param data: A bencoded formatted string
    :param position: The position in which the parser should start
    :return: A string in its pythonic form
    """
    separator = data.find(':')

    if separator == -1:
        raise BencodeException("Missing colon makes it impossible to determine the size of the string.")

    try:
        string_size = int(data[:separator])
    except Exception:
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


def decode_list(data: str):
    if len(data) == 0:
        raise BencodeException("Decoding empty integer is undefined behaviour")

    if data[0] != 'l' or data[-1] != 'e':
        raise BencodeException("Decoding integer with invalid format for lists.")

    position = 1
    while data:

        if data[position] == "i":


decode_list("l4:spami42ee")
