"""Bounded, non-recursive gesture action chains."""
from copy import deepcopy

MACRO_ACTIONS = tuple(f'Macro {index}' for index in range(1, 9))


class MacroBank:
    def __init__(self, allowed, definitions=None):
        self.allowed = frozenset(allowed) - set(MACRO_ACTIONS) - {'None'}
        self.definitions = {}
        self.running = False
        self.load(definitions or {})

    def set(self, name, actions):
        if name not in MACRO_ACTIONS or not isinstance(actions, list) or len(actions) > 8:
            raise ValueError('Choose a macro slot and up to eight actions.')
        if any(not isinstance(action, str) or action not in self.allowed for action in actions):
            raise ValueError('Macro actions must be supported actions or saved scenes. Nested macros are not supported.')
        self.definitions[name] = list(actions)

    def load(self, definitions):
        if not isinstance(definitions, dict):
            raise ValueError('Invalid macro definitions.')
        prepared = {}
        for name, actions in definitions.items():
            if name not in MACRO_ACTIONS or not isinstance(actions, list) or len(actions) > 8:
                raise ValueError('Invalid macro definition.')
            if any(not isinstance(action, str) or action not in self.allowed for action in actions):
                raise ValueError('Unsupported or recursive macro action.')
            prepared[name] = list(actions)
        self.definitions = prepared

    def settings(self):
        return deepcopy(self.definitions)

    def run(self, name, dispatch):
        if self.running:
            return
        actions = tuple(self.definitions.get(name, ()))
        self.running = True
        try:
            for action in actions:
                dispatch(action)
                if action == 'Emergency mute':
                    break
        finally:
            self.running = False

