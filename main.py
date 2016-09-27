#!/usr/bin/python3.5

import logging
import sys
from models import TorrentContainer

PORT = 8889


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    torrent = TorrentContainer(PORT)
    with open(sys.argv[1], 'rb') as f:
        torrent.add_file(f.read())

    torrent_info = torrent.files[0].request_file()
    for peer in torrent_info[b'peers']:
        try:
            handshake = torrent.files[0].handshake(peer)
            print(handshake)
            break
        except Exception as e:
            print(e)
