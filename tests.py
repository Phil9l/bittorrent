#!/usr/bin/python3.5

import unittest
from models import Peer, TorrentFile
from utils import (encode_handshake_data, decode_handshake_data,
                   Bencoder, Bdecoder)


class TestPeersDecoding(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(tuple(TorrentFile._decode_peers(b'')), tuple())

    def test_empty_dict(self):
        self.assertEqual(tuple(TorrentFile._decode_peers([])), tuple())

    def test_wrong_arg_type(self):
        self.assertRaises(ValueError, lambda: TorrentFile._decode_peers(42))

    def test_wrong_list_item_type(self):
        decode = lambda: TorrentFile._decode_peers([{b'ip': b'127.0.0.1',
                                                     b'port': b'80'}, 42])
        self.assertRaises(ValueError, decode)

    def test_common_dict(self):
        data = [{b'ip': b'127.0.0.1', b'port': b'80'},
                 {b'ip': b'192.168.0.1', b'port': b'8080'}]
        result = (Peer(b'127.0.0.1', b'80'), Peer(b'192.168.0.1', b'8080'))
        self.assertEqual(tuple(TorrentFile._decode_peers(data)), result)


class TestBencoder(unittest.TestCase):
    def _test_encoder(self, data, result):
        self.assertEqual(Bencoder.encode(data), result)

    def test_list(self):
        self._test_encoder([], b'le')
        self._test_encoder([1, b'abc', 12], b'li1e3:abci12ee')

    def test_dict(self):
        self._test_encoder({}, b'de')
        self._test_encoder({b'123': 123, b'321': b'321'},
                           b'd3:123i123e3:3213:321e')

    def test_int(self):
        self._test_encoder(1, b'i1e')
        self._test_encoder(42, b'i42e')
        self._test_encoder(-12, b'i-12e')

    def test_string(self):
        self._test_encoder(b'', b'0:')
        self._test_encoder(b'123', b'3:123')


class TestBdecoder(unittest.TestCase):
    def _test_decoder(self, data, result):
        self.assertEqual(Bdecoder.decode(data), result)

    def test_list(self):
        self._test_decoder(b'le', [])
        self._test_decoder(b'li1e3:abci12ee', [1, b'abc', 12])

    def test_dict(self):
        self._test_decoder(b'de', {})
        self._test_decoder(b'd3:123i123e3:3213:321e',
                           {b'123': 123, b'321': b'321'})

    def test_int(self):
        self._test_decoder(b'i1e', 1)
        self._test_decoder(b'i42e', 42)
        self._test_decoder(b'i-12e', -12)

    def test_string(self):
        self._test_decoder(b'0:', b'')
        self._test_decoder(b'3:123', b'123')


if __name__ == '__main__':
    unittest.main()
