"""Report observed runtime counters without claiming measured hardware latency."""
from .runtime import VERSION


def diagnostics_report(engine, camera_active=False):
    converter = engine.converter
    latency = getattr(engine.stream, 'latency', None) if engine.stream else None
    return {
        'version': VERSION,
        'audio_running': bool(engine.stream), 'output_muted': engine.muted,
        'camera_active': camera_active, 'input_peak': round(engine.input_peak, 4),
        'output_peak': round(engine.peak, 4), 'input_near_full_scale_samples': engine.input_clips,
        'audio_status_events': engine.overruns,
        'last_callback_ms': round(engine.callback_ms, 2),
        'max_callback_ms': round(engine.max_callback_ms, 2),
        'reported_device_latency_seconds': latency,
        'audio_error': engine.error, 'plugin_error': engine.rack.error,
        'plugin_bypassed_blocks': engine.rack.bypassed_blocks,
        'ai': None if converter is None else {
            'status': converter.status, 'ready': converter.ready,
            'quality': converter.quality, 'inference_ms': round(converter.inference_ms, 1),
            'chunk_ms': round(converter.hop / 48), 'dropped': converter.dropped,
            'underruns': converter.underruns, 'input_queue': converter.requests.qsize(),
            'result_queue': converter.results.qsize(), 'error': converter.error,
        },
        'recording': bool(engine.recorder), 'recovery_note': 'Device latency is driver reported, not a loopback measurement.',
    }
