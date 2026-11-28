"""Offline, bounded voice comparisons run on the existing inference worker."""
import threading
import time
import numpy as np


class AuditionJob:
    def __init__(self, audio, variants, rate=48000):
        audio = np.asarray(audio, np.float32)
        if audio.ndim != 1 or not rate <= len(audio) <= rate * 8 or not np.isfinite(audio).all():
            raise ValueError('Choose one to eight seconds of finite mono audio.')
        if not 1 <= len(variants) <= 4 or any(quality not in ('Live', 'Studio') for _, quality in variants):
            raise ValueError('Choose up to four Live or Studio voice variants.')
        self.audio, self.variants, self.rate = audio.copy(), tuple(variants), rate
        self.results = []
        self.error = ''
        self.status = 'Queued'
        self.cancel = threading.Event()
        self.done = threading.Event()

    def run(self, backend):
        try:
            for index, (reference, quality) in enumerate(self.variants):
                if self.cancel.is_set():
                    break
                self.status = f'Rendering {index+1}/{len(self.variants)} ({quality})'
                started = time.perf_counter()
                backend.set_reference(reference)
                output = np.zeros_like(self.audio)
                hop = round(self.rate * (.8 if quality == 'Live' else 1.2))
                overlap = round(self.rate * .02)
                for start in range(0, len(self.audio), hop):
                    if self.cancel.is_set():
                        break
                    current = self.audio[start:start+hop]
                    context = self.audio[max(0, start-hop):start]
                    if not len(context):
                        context = np.zeros(hop, np.float32)
                    converted = np.asarray(backend.convert(np.r_[context, current], rate=self.rate,
                                                          steps=8 if quality == 'Studio' else 4), np.float32)
                    if converted.shape != (len(context)+len(current),) or not np.isfinite(converted).all():
                        raise ValueError('The model returned invalid audition audio.')
                    if start:
                        count = min(overlap, start)
                        fade = np.linspace(0, 1, count)
                        previous = converted[-len(current)-count:-len(current)]
                        output[start-count:start] = output[start-count:start] * (1-fade) + previous * fade
                    output[start:start+len(current)] = converted[-len(current):]
                if self.cancel.is_set():
                    break
                self.results.append({'reference': str(reference), 'quality': quality, 'audio': output,
                    'render_ms': (time.perf_counter()-started)*1000,
                    'peak': float(np.max(np.abs(output))),
                    'rms_db': float(20*np.log10(max(1e-9, np.sqrt(np.mean(output.astype(float)**2))))),
                    'near_full_scale': float(np.mean(np.abs(output) >= .999))})
            self.status = 'Cancelled' if self.cancel.is_set() else 'Comparison complete'
        except Exception as exc:
            self.error = str(exc)
            self.status = 'Comparison failed: ' + str(exc)
        finally:
            self.done.set()
