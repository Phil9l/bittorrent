import socket
import hashlib
import urllib.parse
import urllib.request
import logging
import os
from collections import OrderedDict
from datetime import datetime
from exceptions import WrongTorrentFile
from utils import (encode_handshake_data, decode_handshake_data, Bencoder,
                   Bdecoder)


class Peer(object):
    IP_BLOCK_LENGTH = 4

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._hash = hash((host, port))
    
    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def as_tuple(self):
        return self.host, self.port

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, Peer):
            return False
        return (self.host, self.port) == (other.host, other.port)

    def __repr__(self):
        return '<Peer: {}:{}>'.format(self.host, self.port)

    def __str__(self):
        return '{}: {}'.format(self.host, self.port)

    @classmethod
    def from_raw_data(cls, data):
        ip = '.'.join(str(num) for num in data[:cls.IP_BLOCK_LENGTH])
        port = int.from_bytes(data[cls.IP_BLOCK_LENGTH:], 'big')
        return cls(ip, port)

    @classmethod
    def from_dict(cls, data):
        if b'ip' not in data or b'port' not in data:
            raise ValueError('port and ip are required')
        return cls(data[b'ip'], data[b'port'])


class TorrentInfo(object):
    def __init__(self, announce, files, announce_list=None,
                 comment=None, created_by=None, creation_date=None):
        self._announce = announce
        self._files = files
        self._announce_list = announce_list
        self._comment = comment
        self._created_by = created_by
        try:
            self._creation_data = datetime.fromtimestamp(int(creation_date))
        except (ValueError, TypeError):
            self._creation_data = None

    @property
    def announce(self):
        return self._announce

    @property
    def comment(self):
        return self._comment

    @property
    def created_by(self):
        return self._created_by

    @property
    def creation_date(self):
        return self._creation_data

    @property
    def files(self):
        return self._files

    def get_announce_url(self, params):
        data = urllib.parse.urlencode(params)
        return '{}{}{}'.format(self.announce,
                               '&' if '?' in self.announce else '?', data)

    def __repr__(self):
        return '<TorrentInfo>'


class DownloadInfo(object):
    def __init__(self, info):
        self._name = info[b'name']
        self._piece_length = info[b'piece length']
        self._pieces = info[b'pieces']
        self._info_hash = self._get_info_hash(info)

    @property
    def name(self):
        return self._name

    @property
    def piece_length(self):
        return self._piece_length

    @property
    def pieces(self):
        return self._pieces

    @property
    def info_hash(self):
        return self._info_hash

    @staticmethod
    def _get_info_hash(info):
        return hashlib.sha1(Bencoder.encode(info)).digest()


class TorrentFile(object):
    PEER_BLOCK_LENGTH = 6
    IP_BLOCK_LENGTH = 4

    def __init__(self, content, peer_id, port):
        logging.info('Initializing new torrent file')
        self._peer_id = peer_id
        self._port = port
        data = Bdecoder.decode(content)
        try:
            files = self._get_file_info(data[b'info'])
        except KeyError:
            raise WrongTorrentFile

        self.download_info = DownloadInfo(data[b'info'])
        self.torrent_info = TorrentInfo(
            data[b'announce'].decode('utf-8'), files,
            announce_list=data.get(b'announce-list', b''),
            comment=data.get(b'comment', b'').decode('utf-8'),
            created_by=data.get(b'created by', b'').decode('utf-8'),
            creation_date=data.get(b'creation date')
        )

    @staticmethod
    def _get_file_info(info):
        files = []
        for file in info.get(b'files', [info]):
            files.append({'length': file[b'length'],
                          'md5sum': file.get(b'md5sum'),
                          'path': file.get(b'path')})
        return files

    @classmethod
    def _decode_peers(cls, data):
        if isinstance(data, bytes):
            peers = (Peer.from_raw_data(data[pos:pos + cls.PEER_BLOCK_LENGTH])
                     for pos in range(0, len(data), 6))
        elif isinstance(data, list) and all(isinstance(item, dict) or
                                            isinstance(item, OrderedDict)
                                            for item in data):
            peers = (Peer.from_dict(item) for item in data)
        else:
            raise ValueError
        return peers

    def request_file(self):
        params = {
            'info_hash': self.download_info.info_hash,
            'peer_id': self._peer_id,
            'port': self._port,
            'uploaded': 0,
            'downloaded': 0,
            'left': sum(file_data.get('length', 0)
                        for file_data in self.torrent_info.files)
        }

        url = self.torrent_info.get_announce_url(params)
        with urllib.request.urlopen(url) as response:
            result = Bdecoder.decode(response.read())
            result[b'peers'] = self._decode_peers(result.get(b'peers', b''))
        return result

    def handshake(self, peer):
        logging.info('Making a handshake with {}:{}'.format(peer.host,
                                                            peer.port))
        handshake_message = encode_handshake_data(self.download_info.info_hash,
                                                  self._peer_id)

        logging.debug('Handshake message: {}'.format(handshake_message))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(peer.as_tuple)
        logging.info('Connected to peer successfully')
        s.send(handshake_message)
        response_handshake = decode_handshake_data(s.recv(1024))
        logging.debug('Peer answer: {}'.format(response_handshake))
        s.close()
        return response_handshake


class TorrentContainer(object):
    def __init__(self, port):
        self._port = port
        self._peer_id = os.urandom(20)
        self._files = []

    def add_file(self, content):
        self._files.append(TorrentFile(content, self._peer_id, self._port))

    @property
    def files(self):
        return self._files
