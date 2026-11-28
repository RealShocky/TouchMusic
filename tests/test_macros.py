import pytest
from touchmusic.macros import MacroBank


def test_macro_order_snapshot_and_no_recursion():
    bank = MacroBank(['Voice 1', 'Chord I', 'Macro 1', 'Emergency mute'])
    bank.set('Macro 1', ['Voice 1', 'Chord I'])
    calls = []
    bank.run('Macro 1', lambda action: (calls.append(action), bank.run('Macro 1', calls.append)))
    assert calls == ['Voice 1', 'Chord I']
    detached = bank.settings()
    detached['Macro 1'].clear()
    assert len(bank.definitions['Macro 1']) == 2
    with pytest.raises(ValueError):
        bank.set('Macro 1', ['Macro 1'])
    with pytest.raises(ValueError):
        bank.set('Macro 1', ['Chord I'] * 9)
    bank.set('Macro 1', ['Emergency mute', 'Voice 1'])
    calls.clear()
    bank.run('Macro 1', calls.append)
    assert calls == ['Emergency mute']
