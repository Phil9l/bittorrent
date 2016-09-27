from struct import pack, unpack
from collections import namedtuple

HANDSHAKE_FORMAT = '!B19s8s20s20s'
Handshake = namedtuple('Handshake', 'pstrlen pstr reserved info_hash peer_id')


def encode_handshake_data(info_hash, peer_id):
    pstr = b'BitTorrent protocol'
    pstrlen = len(pstr)
    reserved = bytearray(8)
    return pack(HANDSHAKE_FORMAT, pstrlen, pstr, reserved, info_hash, peer_id)


def decode_handshake_data(message):
    handshake = Handshake._make(unpack(HANDSHAKE_FORMAT, message))
    return handshake


class Bencoder(object):
    """ Encodes give data with Bencode encoding. """
    @classmethod
    def _encode_int(cls, data, result):
        """ Encode single int. """
        result.extend((b'i', str(data).encode(), b'e'))

    @classmethod
    def _encode_bool(cls, data, result):
        """ Encode single bool. """
        cls._encode_int(data, result)

    @classmethod
    def _encode_string(cls, data, result):
        """ Encode string. """
        result.extend((str(len(data)).encode(), b':', data))

    @classmethod
    def _encode_list(cls, data, result):
        """ Encode list. """
        result.append(b'l')
        for i in data:
            cls._get_encode_func(type(i))(i, result)
        result.append(b'e')

    @classmethod
    def _encode_dict(cls, data, result):
        """ Encode dict. """
        result.append(b'd')
        for key, value in sorted(data.items()):
            result.extend((str(len(key)).encode(), b':', key))
            cls._get_encode_func(type(value))(value, result)
        result.append(b'e')

    @classmethod
    def _get_encode_func(cls, value_type):
        """ Returns encoding function based on value type. """
        try:
            return {
                int: cls._encode_int,
                bytes: cls._encode_string,
                list: cls._encode_list,
                tuple: cls._encode_list,
                dict: cls._encode_dict,
                bool: cls._encode_bool,
            }[value_type]
        except:
            raise ValueError('Wrong value type')

    @classmethod
    def encode(cls, data):
        """ Encodes given data. """
        result = []
        cls._get_encode_func(type(data))(data, result)
        return b''.join(result)


class Bdecoder(object):
    @classmethod
    def _decode_int(cls, data, offset):
        offset += 1
        new_offset = data.index(b'e', offset)
        num = int(data[offset:new_offset])
        if data[offset] == ord('-'):
            if data[offset + 1] == ord('0'):
                raise ValueError()
        elif data[offset] == ord('0') and new_offset != offset + 1:
            raise ValueError()
        return num, new_offset + 1

    @classmethod
    def _decode_string(cls, data, offset):
        colon_pos = data.index(b':', offset)
        num = int(data[offset:colon_pos])
        if data[offset] == ord('0') and colon_pos != offset + 1:
            raise ValueError()
        result_string = data[colon_pos + 1:colon_pos + num + 1]
        return result_string, colon_pos + num + 1

    @classmethod
    def _decode_list(cls, data, offset):
        result = []
        offset += 1
        while data[offset] != ord('e'):
            item, offset = cls._decode_function(data[offset])(data, offset)
            result.append(item)
        return result, offset + 1

    @classmethod
    def _decode_dict(cls, data, offset):
        result = {}
        offset += 1
        while data[offset] != ord('e'):
            key, offset = cls._decode_string(data, offset)
            result[key], offset = cls._decode_function(data[offset])(data,
                                                                     offset)
        return result, offset + 1

    @classmethod
    def _decode_function(cls, label):
        result_function = {ord(str(num)): cls._decode_string
                           for num in range(0, 10)}
        result_function[ord('l')] = cls._decode_list
        result_function[ord('d')] = cls._decode_dict
        result_function[ord('i')] = cls._decode_int
        return result_function[label]

    @classmethod
    def decode(cls, data):
        try:
            result, offset = cls._decode_function(data[0])(data, 0)
        except (IndexError, KeyError, ValueError):
            raise ValueError("Bad input")
        if offset != len(data):
            raise ValueError("Bad input")
        return result
