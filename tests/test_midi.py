from touchmusic.midi import MidiOutput


class Port:
    def __init__(self):
        self.messages = []
        self.opened = False

    def get_ports(self):
        return ['TouchMusic test']

    def open_port(self, index, name):
        self.opened = True

    def close_port(self):
        self.opened = False

    def send_message(self, message):
        self.messages.append(message)


def test_midi_channels_cc_throttle_and_timed_notes():
    port = Port()
    now = [0.]
    output = MidiOutput(lambda: port, lambda: now[0])
    output.connect('TouchMusic test', channel=3)
    output.control(74, .5)
    output.control(74, .5)
    output.control(74, .8)
    assert port.messages == [[0xB2, 74, 64]]
    now[0] = .04
    output.control(74, .8)
    output.play([60, 64, 67], duration=.5)
    assert [0x92, 60, 100] in port.messages
    now[0] = 1.
    output.tick()
    assert [0x82, 60, 0] in port.messages
    assert not output.notes
    output.close()
    assert [0xB2, 123, 0] in port.messages
    assert not port.opened


def test_device_failure_disconnects_and_clears_notes():
    port = Port()
    output = MidiOutput(lambda: port)
    output.connect('TouchMusic test')
    output.play([60])
    port.send_message = lambda _: (_ for _ in ()).throw(RuntimeError('device disconnected'))
    output.control(1, .5)
    assert output.backend is None
    assert not output.notes
    assert 'device disconnected' in output.error
