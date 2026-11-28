"""Opt-in loopback-only VST3 control transport. No audio or remote commands."""
import json
import math
import socket
import threading
import time

PROTOCOL = 'touchmusic-control/1'
PORT = 26789


def decode_packet(raw):
    if len(raw) > 2048:
        raise ValueError('Oversized bridge packet.')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('protocol') != PROTOCOL:
        raise ValueError('Unsupported bridge protocol.')
    identity = data.get('instance')
    if not isinstance(identity, str) or not identity.isalnum() or not 1 <= len(identity) <= 64:
        raise ValueError('Invalid plugin instance.')
    sequence = data.get('sequence')
    if type(sequence) is not int or not 0 <= sequence < 2**53:
        raise ValueError('Invalid sequence.')
    parameters = data.get('parameters')
    if (not isinstance(parameters, list) or len(parameters) != 10 or any(
            type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1 for value in parameters)):
        raise ValueError('Invalid automation parameters.')
    if type(data.get('playing')) is not bool:
        raise ValueError('Invalid transport state.')
    for key, lower, upper in [('tempo', 20, 400), ('ppq', -1e9, 1e9),
                               ('sample_rate', 8000, 384000), ('sample_position', -2**53, 2**53)]:
        value = data.get(key)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper):
            raise ValueError('Invalid host timing.')
    return data


class LocalBridge:
    def __init__(self, port=PORT):
        self.port = port
        self.socket = None
        self.thread = None
        self.stop_event = threading.Event()
        self.latest = None
        self.active_instance = None
        self.sequence = -1
        self.consumed = None
        self.packets = self.rejected = 0
        self.error = ''

    def start(self):
        if self.socket:
            return
        channel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            channel.bind(('127.0.0.1', self.port))
            channel.settimeout(.2)
        except Exception:
            channel.close()
            raise
        self.socket = channel
        self.port = channel.getsockname()[1]
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name='TouchMusic control bridge')
        self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                raw, sender = self.socket.recvfrom(2049)
                if sender[0] != '127.0.0.1':
                    continue
                data = decode_packet(raw)
                if self.active_instance is None:
                    self.active_instance = data['instance']
                if data['instance'] != self.active_instance or data['sequence'] <= self.sequence:
                    self.rejected += 1
                    continue
                self.sequence = data['sequence']
                self.packets += 1
                self.latest = {**data, 'received_at': time.monotonic()}
            except socket.timeout:
                continue
            except (ValueError, TypeError, UnicodeError):
                self.rejected += 1
            except OSError as exc:
                if not self.stop_event.is_set():
                    self.error = str(exc)
                return

    def consume(self):
        packet = self.latest
        if packet is not None and (packet['instance'], packet['sequence']) != self.consumed:
            self.consumed = packet['instance'], packet['sequence']
            return packet

    def reset_source(self):
        self.active_instance = None
        self.sequence = -1
        self.latest = self.consumed = None

    def close(self):
        self.stop_event.set()
        if self.socket:
            self.socket.close()
            if self.thread:
                self.thread.join(.5)
        self.socket = None
