"""Opt-in DAW-clocked stereo audio return, independent of PortAudio and MIDI."""
import socket
import struct
import threading
import time
import numpy as np

PORT = 26790
HEADER = struct.Struct('<IIQQIHH')
MAGIC = 0x31414D54
FRAMES = 512
SIZE = HEADER.size + FRAMES*2*4


def encode_packet(instance, frame, audio, kind=1):
    audio = np.asarray(audio, dtype='<f4')
    if audio.shape != (FRAMES, 2) or not np.isfinite(audio).all():
        raise ValueError('Invalid bridge PCM.')
    return HEADER.pack(MAGIC, kind, instance, frame, 48000, 2, FRAMES)+audio.tobytes()


def decode_packet(raw, kind=1):
    if len(raw) != SIZE:
        raise ValueError('Invalid audio packet length.')
    magic, actual, instance, frame, rate, channels, frames = HEADER.unpack_from(raw)
    if (magic != MAGIC or actual != kind or not instance or frame % FRAMES
            or frame >= 2**53 or rate != 48000 or channels != 2 or frames != FRAMES):
        raise ValueError('Unsupported audio bridge packet. Use 48 kHz.')
    audio = np.frombuffer(raw, dtype='<f4', offset=HEADER.size).reshape(FRAMES, 2).copy()
    if not np.isfinite(audio).all():
        raise ValueError('Non-finite bridge audio.')
    return instance, frame, audio


class AudioBridge:
    def __init__(self, engine, port=PORT):
        self.engine, self.port = engine, port
        self.socket = None
        self.thread = None
        self.stop_event = threading.Event()
        self.active = None
        self.last_frame = -FRAMES
        self.received_at = 0.
        self.packets = self.rejected = self.gaps = 0
        self.error = ''

    def start(self):
        if self.socket:
            return
        if self.engine.stream:
            raise ValueError('Stop standalone microphone audio before enabling DAW audio.')
        if self.engine.rack.editor_open or self.engine.rack.editor_pending:
            raise ValueError('Close the native editor first.')
        channel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            channel.bind(('127.0.0.1', self.port))
            channel.settimeout(.1)
            self.engine.rack.reset_stream()
            self.engine.instrument.reset_stream()
            if self.engine.converter:
                self.engine.converter.reset()
        except Exception:
            channel.close()
            raise
        self.engine.external = True
        self.socket = channel
        self.port = channel.getsockname()[1]
        self.active = None
        self.error = ''
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name='TouchMusic DAW audio')
        self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                raw, sender = self.socket.recvfrom(SIZE+1)
                if sender[0] != '127.0.0.1':
                    continue
                identity, frame, audio = decode_packet(raw)
                now = time.monotonic()
                source = (identity, sender)
                if self.active is None or (source != self.active and now-self.received_at > .5):
                    self.active = source
                    self.last_frame = frame-FRAMES
                    self.engine.rack_origins.fill(-1)
                    if self.engine.converter:
                        self.engine.converter.reset()
                if source != self.active or frame <= self.last_frame:
                    self.rejected += 1
                    continue
                gap = (frame-self.last_frame)//FRAMES-1
                self.gaps += gap
                if gap > 8 and self.engine.converter:
                    self.engine.converter.reset()
                for _ in range(min(gap, 8)):
                    self.engine.process(np.zeros(FRAMES, np.float32), stereo=True)
                self.engine.clock.frame = frame
                wet = self.engine.process(audio.mean(axis=1), stereo=True)
                self.socket.sendto(encode_packet(identity, frame, wet, kind=2), sender)
                self.last_frame, self.received_at = frame, now
                self.packets += 1
            except socket.timeout:
                continue
            except (ValueError, TypeError):
                self.rejected += 1
            except Exception as exc:
                if not self.stop_event.is_set():
                    self.error = str(exc)
                return

    def close(self):
        self.stop_event.set()
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                self.error = 'DAW audio thread is still stopping.'
                return False
        self.socket, self.thread = None, None
        self.engine.external = False
        self.engine.instrument.panic()
        return True
