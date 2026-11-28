"""Audio transport, playback, loop capture and effects."""
from pathlib import Path
import queue
import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from .music import ChordPad, SCALES, chord_notes, nearest_note
from .transport import BeatClock
from .vocal import FormantShifter, VocalAnalysis, harmony_shift
from .alignment import align_recording, mix_stems

RATE = 48000
BLOCK = 512
LOOP_COUNT = 4
LOOP_SECONDS = 120
STEM_NAMES = ('dry-mic', 'wet-vocal', *(f'loop-{i}' for i in range(1, LOOP_COUNT + 1)),
              'backing', 'chords')


class SamplePlayer:
    def __init__(self):
        self.audio = np.zeros(0, np.float32)
        self.position = 0
        self.playing = False
        self.gain = .6
        self.lock = threading.Lock()

    def load(self, audio):
        prepared = np.asarray(audio, dtype=np.float32)
        with self.lock:
            self.playing = False
            self.audio = prepared
            self.position = 0

    def restart(self):
        with self.lock:
            self.position = 0
            self.playing = bool(len(self.audio))

    def toggle(self):
        with self.lock:
            if self.position >= len(self.audio):
                self.position = 0
            self.playing = bool(len(self.audio)) and not self.playing

    def read(self, count):
        output = np.zeros(count, np.float32)
        if not self.lock.acquire(blocking=False):
            return output
        try:
            if self.playing:
                end = min(self.position + count, len(self.audio))
                available = end - self.position
                output[:available] = self.audio[self.position:end]
                self.position = end
                self.playing = end < len(self.audio)
        finally:
            self.lock.release()
        return output


class LoopTrack:
    def __init__(self, rate):
        self.rate = rate
        self.gain = .7
        self.muted = False
        self.seam_ms = 0
        self.feedback = 1.
        self.clear()

    def clear(self):
        self.recording = False
        self.size = 0
        self.position = 0
        self.clip = None
        self.buffer = None
        self.overdubbing = False
        self.history = []
        self.future = []

    @property
    def previous(self):
        return self.history[-1] if self.history else None

    @previous.setter
    def previous(self, clip):
        self.history = [clip] if clip is not None else []
        self.future = []

    def _commit(self, clip):
        if self.clip is not None:
            self.history = [*self.history[-3:], self.clip]
        self.future = []
        self.clip = clip

    def start_overdub(self, feedback=1.):
        if self.recording or self.clip is None:
            return
        self.buffer = self.clip.copy()
        self.feedback = max(0., min(1., feedback))
        self.recording = self.overdubbing = True

    def toggle(self):
        if self.recording:
            if self.overdubbing:
                self._commit(self.buffer)
            elif self.size:
                self._commit(self.buffer[:self.size].copy())
                self.position = 0
            self.buffer = None
            self.recording = self.overdubbing = False
            self.size = len(self.clip) if self.clip is not None else 0
        else:
            self.size = 0
            self.buffer = np.empty(self.rate * LOOP_SECONDS, np.float32)
            self.recording = True

    def load(self, clip):
        self.clear()
        self.clip = clip
        self.size = len(clip) if clip is not None else 0

    def undo(self):
        if not self.recording and self.history:
            self.future.append(self.clip)
            self.clip = self.history.pop()
            self.size = len(self.clip)
            self.position %= self.size

    def redo(self):
        if not self.recording and self.future:
            self.history.append(self.clip)
            self.clip = self.future.pop()
            self.size = len(self.clip)
            self.position %= self.size

    def process(self, audio):
        if self.overdubbing:
            output = np.zeros_like(audio)
            offset = 0
            while offset < len(audio):
                count = min(len(audio) - offset, len(self.buffer) - self.position)
                target = slice(self.position, self.position + count)
                if not self.muted:
                    output[offset:offset+count] = self.buffer[target]
                self.buffer[target] = self.buffer[target] * self.feedback + audio[offset:offset+count]
                offset += count
                self.position = (self.position + count) % len(self.buffer)
            return output
        if self.recording:
            count = min(len(audio), len(self.buffer) - self.size)
            self.buffer[self.size:self.size + count] = audio[:count]
            self.size += count
            if self.size >= self.rate * LOOP_SECONDS:
                self.toggle()
            return np.zeros_like(audio)
        output = np.zeros_like(audio)
        clip = self.clip
        if clip is not None:
            indices = (np.arange(len(audio)) + self.position) % len(clip)
            if not self.muted:
                output[:] = clip[indices]
                fade = min(round(self.seam_ms * self.rate / 1000), len(clip) // 2)
                if fade:
                    output *= np.minimum(1., np.minimum(indices, len(clip)-1-indices) / fade)
            self.position = int((self.position + len(audio)) % len(clip))
        return output


class PitchVoice:
    """Shift live audio using two crossfaded variable delay taps."""
    window = 1920

    def reset(self):
        self.history = np.zeros(self.window + 2, np.float32)
        self.phase = 0.

    def process(self, audio, semitones, window=None):
        samples = np.arange(len(audio))
        window = self.window if window is None else window
        step = (1 - 2 ** (semitones / 12)) / window
        phase = (self.phase + samples * step) % 1
        other_phase = (phase + .5) % 1
        self.phase = (self.phase + len(audio) * step) % 1
        waveform = np.concatenate((self.history, audio))
        self.history = waveform[-len(self.history):].copy()
        clock = samples + len(self.history)
        grid = np.arange(len(waveform))
        first = np.interp(clock - phase * window, grid, waveform)
        second = np.interp(clock - other_phase * window, grid, waveform)
        weight = np.sin(np.pi * phase) ** 2
        return (first * weight + second * (1 - weight)).astype(np.float32)


class Recorder:
    def __init__(self, path, stems=False, align=False):
        self.queue = queue.Queue(maxsize=512)
        self.dropped = 0
        self.error = ''
        path = Path(path)
        self.stem_dir = path.with_name(path.stem + '-stems') if stems or align else None
        self.provenance = self.stem_dir / 'vocal-origin.i64' if align else None
        self.recording_start = None
        self.alignment_thread = None
        self.alignment_error = ''
        self.aligned_mix = None
        self.files = []
        if self.stem_dir:
            self.stem_dir.mkdir()
        paths = [path]
        if self.stem_dir:
            paths.extend(self.stem_dir / (name + '.wav') for name in STEM_NAMES)
        try:
            for target in paths:
                self.files.append(sf.SoundFile(str(target), 'w', RATE, 1, subtype='PCM_24'))
        except Exception:
            for file in self.files:
                file.close()
            raise
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def write(self, audio, stems=(), frame=0, origins=None):
        try:
            self.queue.put_nowait(((audio, *stems), frame, origins))
        except queue.Full:
            self.dropped += 1

    def _run(self):
        mapping = None
        try:
            if self.provenance:
                mapping = self.provenance.open('wb')
            while True:
                block = self.queue.get()
                if block is None:
                    break
                signals, frame, origins = block
                for file, signal in zip(self.files, signals):
                    file.write(signal)
                if mapping:
                    if self.recording_start is None:
                        self.recording_start = frame
                    if origins is None:
                        origins = np.arange(frame, frame + len(signals[0]), dtype=np.int64)
                    mapping.write(np.asarray(origins, dtype='<i8').tobytes())
        except Exception as exc:
            self.error = str(exc)
        finally:
            if mapping:
                mapping.close()
            for file in self.files:
                file.close()

    def close(self, master_gain=1.):
        while self.thread.is_alive():
            try:
                self.queue.put(None, timeout=.1)
                break
            except queue.Full:
                continue
        self.thread.join(timeout=5)
        if self.provenance and self.recording_start is not None and not self.error:
            if self.dropped or self.thread.is_alive():
                self.alignment_error = 'Recording blocks were dropped or are still writing.'
                return
            self.alignment_thread = threading.Thread(target=self._export_aligned, args=(master_gain,), daemon=False)
            self.alignment_thread.start()

    def _export_aligned(self, gain):
        try:
            wet = self.stem_dir / 'wet-vocal-aligned.wav'
            align_recording(self.stem_dir / 'wet-vocal.wav', self.provenance, wet, self.recording_start)
            mix = self.stem_dir / 'performance-aligned.wav'
            accompaniment = [self.stem_dir / (name + '.wav') for name in STEM_NAMES[2:]]
            mix_stems([wet, *accompaniment], mix, master_gain=gain)
            self.provenance.unlink(missing_ok=True)
            self.aligned_mix = mix
        except Exception as exc:
            self.alignment_error = str(exc)


class AudioEngine:
    def __init__(self):
        from pedalboard import (Pedalboard, Reverb, Delay, Compressor, HighpassFilter,
                                LowpassFilter, Chorus, Distortion, NoiseGate, LowShelfFilter, HighShelfFilter)
        self.pitch = PitchVoice()
        self.pitch.reset()
        self.tuning = PitchVoice()
        self.tuning.reset()
        self.analysis = VocalAnalysis(RATE)
        self.harmony_analysis = VocalAnalysis(RATE)
        self.formants = FormantShifter(RATE)
        self.formant_origins = None
        self.formant_active = False
        self.pad = ChordPad(RATE)
        self.tune_shift = 0.
        self.tune_window = self.tuning.window
        self.detected_note = None
        self.target_note = None
        self.pitch_cents = 0
        self.reverb = Reverb(room_size=.6, wet_level=0, dry_level=1)
        self.delay = Delay(delay_seconds=.3, feedback=.25, mix=0)
        self.chorus = Chorus(rate_hz=1.2, depth=.30, centre_delay_ms=12, mix=0)
        self.gate = NoiseGate(threshold_db=-100, ratio=4, attack_ms=2, release_ms=120)
        self.warmth = LowShelfFilter(cutoff_frequency_hz=230)
        self.brightness = HighShelfFilter(cutoff_frequency_hz=3200)
        self.board = Pedalboard([HighpassFilter(cutoff_frequency_hz=70), self.gate,
                                self.warmth, self.brightness, Compressor(threshold_db=-18, ratio=3),
                                self.chorus, self.delay, self.reverb])
        self.radio = Pedalboard([HighpassFilter(cutoff_frequency_hz=400), LowpassFilter(cutoff_frequency_hz=2700)])
        self.drive = Distortion(drive_db=14)
        self.harmony = PitchVoice()
        self.harmony.reset()
        self.octave = PitchVoice()
        self.octave.reset()
        self.params = {'pitch': 0., 'reverb': 0., 'delay': 0., 'harmony': 0., 'robot': 0., 'gain': .7,
                       'chorus': 0., 'drive': 0., 'radio': 0., 'octave': 0., 'tremolo': 0.,
                       'warmth': 0., 'brightness': 0., 'gate': 0., 'feedback': .29, 'delaytime': .3,
                       'dialogue': False, 'aimix': 1., 'master': 1., 'monitor': 'Wet vocal',
                       'key': 0, 'scale': 'Major', 'tune': 0., 'retune': .45, 'tune_target': 'Key / scale',
                       'chord': 0, 'chord_enabled': False, 'chord_level': .45,
                       'bpm': 120, 'quantize': 'Immediate', 'metronome': False, 'loop_input': 'Processed vocal',
                       'vocal_range': 'Wide', 'vibrato': 0., 'formant': 0., 'harmony_mode': 'Fixed fifth',
                       'count_in': 0, 'capture_bars': 0, 'loop_mode': 'Replace', 'overdub_feedback': 1.,
                       'seam_ms': 0}
        self.clock = BeatClock(RATE)
        self.track, self.preview = SamplePlayer(), SamplePlayer()
        self.loops = [LoopTrack(RATE) for _ in range(LOOP_COUNT)]
        self.loop = self.loops[0]
        self.commands = queue.SimpleQueue()
        self.recorder = None
        self.stream = None
        self.converter = None
        self.neural = False
        self.muted = False
        self.peak = 0.
        self.input_peak = 0.
        self.overruns = 0
        self.error = ''
        self.phase = 0

    def apply_loop_commands(self):
        self._read_commands('Immediate')

    @property
    def queued_chord(self):
        event = self.clock.pending.get(('chord', 0))
        return event[1][1] if event else None

    def _read_commands(self, mode):
        while not self.commands.empty():
            command = self.commands.get_nowait()
            action, index = command if isinstance(command, tuple) else (command, 0)
            pending = self.clock.pending
            key = action, index if action != 'chord' else 0
            if action == 'clear':
                for queued in ('loop', 'overdub', 'restart', 'finish'):
                    self.clock.discard((queued, index))
            capturing = action in ('loop', 'overdub')
            if capturing and key in pending:
                self.clock.discard(key)
            elif capturing and not self.loops[index].recording and self.params['count_in']:
                boundary = self.clock.boundary('Next beat' if mode == 'Immediate' else mode)
                frame = boundary + round(self.params['count_in'] * 4 * self.clock.period)
                self.clock.queue_at(key, (action, index), frame, keep_beats=True)
            elif mode != 'Immediate' and action in ('loop', 'overdub', 'restart', 'chord'):
                self.clock.queue_at(key, (action, index), self.clock.boundary(mode))
            else:
                self.clock.discard(key)
                self._apply_command(action, index)

    def _apply_command(self, action, index):
        if action == 'chord':
            self.params['chord'] = index
            return
        track = self.loops[index]
        if action in ('loop', 'overdub'):
            self.clock.discard(('finish', index))
            for other_index, other in enumerate(self.loops):
                if other is not track and other.recording:
                    other.toggle()
                    self.clock.discard(('finish', other_index))
            if track.recording:
                track.toggle()
            elif track.clip is not None and (action == 'overdub' or self.params['loop_mode'] == 'Overdub'):
                track.start_overdub(self.params['overdub_feedback'])
            elif action == 'loop':
                track.toggle()
            bars = self.params['capture_bars']
            if track.recording and bars:
                size = len(track.clip) if track.overdubbing else round(bars * 4 * self.clock.period)
                self.clock.queue_at(('finish', index), ('finish', index), self.clock.frame + size, keep_beats=True)
        elif action == 'finish':
            if track.recording:
                track.toggle()
        elif action == 'clear':
            track.clear()
            track.previous = None
        elif action == 'mute':
            track.muted = not track.muted
        elif action == 'restart':
            track.position = 0
        elif action == 'undo':
            track.undo()
        elif action == 'redo':
            track.redo()

    def tune_vocal(self, audio, p, chord, detected):
        pitch = self.analysis.pitch
        shift = 0.
        self.detected_note = self.target_note = None
        if detected is not None:
            choices = chord if p['tune_target'] == 'Current chord' else (
                range(12) if p['tune_target'] == 'Chromatic' else
                [p['key'] + note for note in SCALES[p['scale']]])
            self.detected_note = round(detected)
            center = self.analysis.center if p['vibrato'] else detected
            self.target_note = nearest_note(center, choices)
            self.pitch_cents = round(100 * (detected - self.target_note))
            shift = np.clip(self.analysis.correction(detected, self.target_note, p['vibrato']), -3., 3.) * p['tune']
            period = RATE / pitch
            # Keep crossfaded taps separated by whole voice cycles to avoid cancellation.
            self.tune_window = 2 * period * max(1, int(960 / period))
        speed = .06 + .94 * p['retune'] if pitch else .65
        self.tune_shift += (shift - self.tune_shift) * speed
        corrected = self.tuning.process(audio, self.tune_shift, window=self.tune_window)
        wet = min(1., abs(self.tune_shift) * 30.)
        return audio * (1. - wet) + corrected * wet

    def process(self, audio):
        mode = self.params['quantize']
        clock = self.clock
        clock.set_tempo(self.params['bpm'], mode)
        self._read_commands(mode)
        end = clock.frame + len(audio)
        offset = 0
        blocks = []
        while clock.pending:
            key, (frame, command) = min(clock.pending.items(), key=lambda item: item[1][0])
            if frame >= end:
                break
            size = max(0, frame - clock.frame)
            if size:
                blocks.append(self._render(audio[offset:offset+size]))
                clock.frame += size
                offset += size
            clock.discard(key)
            self._apply_command(*command)
        blocks.append(self._render(audio[offset:]))
        clock.frame = end
        return blocks[0] if len(blocks) == 1 else np.concatenate(blocks)

    def _render(self, audio):
        p = self.params.copy()
        recorder = self.recorder
        self.input_peak = float(np.max(np.abs(audio)))
        dry = audio
        chord = chord_notes(p['key'], p['scale'], p['chord'])
        chords_follow = p['harmony'] and p['harmony_mode'] != 'Fixed fifth'
        analyzing = not p['dialogue'] and (p['tune'] or chords_follow)
        detected = self.analysis.process(audio, p['vocal_range']) if analyzing else None
        if p['tune'] and not p['dialogue']:
            audio = self.tune_vocal(audio, p, chord, detected)
        else:
            self.detected_note = self.target_note = None
            self.tune_shift = 0.
        loop_mic = audio
        converter = self.converter if self.neural else None
        origins = None
        if converter:
            audio = converter.process(audio, mix=p['aimix'], start_frame=self.clock.frame)
            origins = converter.source_frames
        if p['formant'] and not p['dialogue']:
            if self.formant_origins is None:
                self.formant_origins = np.full(self.formants.size, -1, np.int64)
            if origins is None:
                origins = np.arange(self.clock.frame, self.clock.frame + len(audio), dtype=np.int64)
            frames = np.concatenate((self.formant_origins, origins))
            self.formant_origins = frames[-self.formants.size:]
            origins = frames[:len(audio)]
            audio = self.formants.process(audio, p['formant'])
            self.formant_active = True
        elif self.formant_active:
            self.formants.reset()
            self.formant_origins = None
            self.formant_active = False
        harmony_note = self.analysis.center
        if harmony_note is not None:
            harmony_note += self.tune_shift
        if converter and chords_follow and not p['dialogue']:
            self.harmony_analysis.process(audio, p['vocal_range'])
            harmony_note = self.harmony_analysis.center
        interval = harmony_shift(harmony_note, chord, p['harmony_mode'])
        vocal = (audio if p['dialogue'] else self.vocal_effects(audio, p, interval)) * p['gain']
        capture = loop_mic * p['gain'] if p['loop_input'] == 'Mic before AI' else vocal
        accompaniment = np.zeros_like(audio)
        loop_stems = []
        for track in self.loops:
            track.seam_ms = p['seam_ms']
            stem = track.process(capture) * track.gain if track.recording or track.clip is not None else np.zeros_like(audio)
            accompaniment += stem
            loop_stems.append(stem)
        backing = self.track.read(len(audio)) * self.track.gain
        chords = self.pad.process(len(audio), chord, p['chord_level'] if p['chord_enabled'] else 0)
        accompaniment += backing + chords
        if recorder:
            mix = np.tanh((vocal + accompaniment) * p['master'])
            stems = (dry, vocal, *loop_stems, backing, chords) if recorder.stem_dir else ()
            recorder.write(mix, stems, self.clock.frame, origins)
        heard = dry * p['gain'] if p['monitor'] == 'Dry mic' else vocal
        preview = self.preview.read(len(audio)) * .65
        counting = any(key[0] in ('loop', 'overdub') and key in self.clock.beat_targets
                       for key in self.clock.pending)
        click = self.clock.click(len(audio)) if p['metronome'] or counting else 0
        output = np.tanh((heard + accompaniment + preview + click) * p['master']).astype(np.float32)
        if self.muted:
            output.fill(0)
        self.peak = float(np.max(np.abs(output)))
        return output

    def vocal_effects(self, audio, p, interval=7):
        self.delay.mix = p['delay']
        self.delay.delay_seconds = p['delaytime']
        self.delay.feedback = p['feedback'] * .85
        self.gate.threshold_db = -100 + p['gate'] * 65
        self.warmth.gain_db = p['warmth'] * 12
        self.brightness.gain_db = p['brightness'] * 12
        self.chorus.mix = p['chorus'] * .7
        self.reverb.wet_level = p['reverb'] * .6
        self.reverb.dry_level = 1 - p['reverb'] * .3
        harmony = self.harmony.process(audio, interval or 7)
        pitched = self.pitch.process(audio, p['pitch']) if p['pitch'] else audio
        octave = self.octave.process(audio, -12)
        harmony_level = p['harmony'] * .5 if interval is not None else 0.
        vocal = self.board(pitched, RATE, reset=False) + harmony * harmony_level + octave * p['octave'] * .55
        if p['radio']:
            vocal = vocal * (1 - p['radio']) + self.radio(vocal, RATE, reset=False) * p['radio']
        if p['drive']:
            vocal = vocal * (1 - p['drive']) + self.drive(vocal, RATE, reset=False) * p['drive']
        phase = (np.arange(len(audio)) + self.phase) * (2 * np.pi / RATE)
        self.phase = (self.phase + len(audio)) % RATE
        vocal = vocal * (1 - p['robot'] + p['robot'] * np.sin(phase * 85))
        return vocal * (1 - p['tremolo'] * .5 * (1 - np.sin(phase * 5)))

    def _callback(self, inputs, outputs, frames, timing, status):
        try:
            if status:
                self.overruns += 1
            result = self.process(inputs[:, 0].copy())
            outputs[:] = result[:, None]
        except Exception as exc:
            outputs.fill(0)
            self.error = str(exc)

    def start(self, input_device, output_device):
        input_info = sd.query_devices(input_device, 'input')
        output_info = sd.query_devices(output_device, 'output')
        if input_info['hostapi'] != output_info['hostapi']:
            raise ValueError('Select a microphone and output using the same Windows audio backend.')
        api = sd.query_hostapis(input_info['hostapi'])['name']
        settings = None
        if api == 'Windows WASAPI':
            settings = (sd.WasapiSettings(auto_convert=True), sd.WasapiSettings(auto_convert=True))
        self.stop()
        self.clock = BeatClock(RATE)
        self.clock.set_tempo(self.params['bpm'], self.params['quantize'])
        self.error = ''
        self.board.reset()
        self.radio.reset()
        self.pitch.reset()
        self.tuning.reset()
        self.analysis.reset()
        self.harmony_analysis.reset()
        self.formants.reset()
        self.formant_active = False
        self.formant_origins = None
        self.pad = ChordPad(RATE)
        self.harmony.reset()
        self.octave.reset()
        if self.converter:
            self.converter.reset()
        stream = sd.Stream(device=(input_device, output_device), samplerate=RATE, blocksize=BLOCK,
                           channels=(1, 2), dtype='float32', callback=self._callback, latency='low',
                           extra_settings=settings)
        try:
            stream.start()
        except Exception:
            stream.close()
            raise
        self.stream = stream

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            for track in self.loops:
                if track.recording:
                    track.toggle()
            while not self.commands.empty():
                self.commands.get_nowait()
            self.clock.pending.clear()
            self.clock.beat_targets.clear()
        return self.stop_recording()

    def start_recording(self, path, stems=False, align=False):
        if not self.stream:
            raise ValueError('Start audio before recording.')
        self.stop_recording()
        self.recorder = Recorder(path, stems=stems, align=align)

    def stop_recording(self):
        recorder, self.recorder = self.recorder, None
        if recorder:
            recorder.close(self.params['master'])
        return recorder
