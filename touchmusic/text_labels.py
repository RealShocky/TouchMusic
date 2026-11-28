"""Readable scene actions with compatibility for earlier punctuation encodings."""
from copy import deepcopy

SCENE_PREFIX = 'Scene | '
LEGACY_SCENE_PREFIXES = ('Scene \xc3\u0192\xc6\u2019\xc3\u2020\xe2\u20ac\u2122\xc3\u0192\xc2\xa2\xc3\xa2\xe2\u20ac\u0161\xc2\xac\xc3\u2026\xc2\xa1\xc3\u0192\xc6\u2019\xc3\xa2\xe2\u201a\xac\xc5\xa1\xc3\u0192\xe2\u20ac\u0161\xc3\u201a\xc2\xb7 ', 'Scene \xc3\u0192\xc6\u2019\xc3\xa2\xe2\u201a\xac\xc5\xa1\xc3\u0192\xe2\u20ac\u0161\xc3\u201a\xc2\xb7 ', 'Scene \xc3\u0192\xe2\u20ac\u0161\xc3\u201a\xc2\xb7 ', 'Scene \xc3\u201a\xc2\xb7 ', 'Scene \xc2\xb7 ', 'Scene \xb7 ')  # Historical action prefixes inserted as ASCII escapes.


def scene_action(value):
    if isinstance(value, str):
        for prefix in LEGACY_SCENE_PREFIXES:
            if value.startswith(prefix):
                return SCENE_PREFIX+value[len(prefix):]
    return value


def score_labels(settings):
    result = deepcopy(settings)
    if isinstance(result, dict) and isinstance(result.get('events'), list):
        for event in result['events']:
            if isinstance(event, dict) and event.get('kind') == 'action':
                event['target'] = scene_action(event.get('target'))
    return result


def saved_labels(settings):
    """Migrate action fields only, preserving user names, paths and references."""
    result = deepcopy(settings)
    if not isinstance(result, dict):
        return result
    if isinstance(result.get('mapping'), dict):
        result['mapping'] = {key: scene_action(value) for key, value in result['mapping'].items()}
    if isinstance(result.get('macros'), dict):
        result['macros'] = {key: [scene_action(a) for a in actions] if isinstance(actions, list) else actions
                            for key, actions in result['macros'].items()}
    if 'motion_score' in result:
        result['motion_score'] = score_labels(result['motion_score'])
    for key in ('presets', 'scenes'):
        if isinstance(result.get(key), dict):
            result[key] = {name: saved_labels(preset) for name, preset in result[key].items()}
    return result
