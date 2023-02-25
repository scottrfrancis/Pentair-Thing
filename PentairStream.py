# PentairStream
#
#   The processing stream from input connection to output state
#

from Observer import *
from PentairProtocol import PentairProtocol

# takes a stream on #update and writes it to the messages object, using messages#append
class MessageParser(Observer):
    def __init__(self, separator, messages):
        super().__init__()
        self.separator = separator
        self.messages = messages

    def update(self, stream):
        self.parseStream(stream)

    def parseStream(self, stream):
        if len(stream) > 0:
            self.messages.append(stream.split(self.separator))


# takes messsages and parses to frames
class FrameParser(Observer):
    def __init__(self, frames):
        super().__init__()
        self.protocol = PentairProtocol()

        self.frames = frames

    def update(self, messages):
        self.frames.append(list(map(self.protocol.parseFrame, messages)))

class StateAggregator(Observer):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def update(self, parsedFrames):
        for p in parsedFrames:
            if 'state' in p:
                self.state.append(p['state'])

class PentairStream:
    def __init__(self, connection):
        self.connection = connection

        self.streamData = ObservableString()
        self.messages = ObservableArray()
        self.frames = ObservableArray()
        self.state = ObservableDict()

        # messageParser will chop the stream into separate messages
        self.messageParser = MessageParser(PentairProtocol.RECORD_SEPARATOR, self.messages)
        # connect messageParser as an oberver of streamData
        self.streamData.addObserver(self.messageParser)

        self.frameParser = FrameParser(self.frames)
        self.messages.addObserver(self.frameParser)

        self.state = ObservableDict()
        self.stateAggregator = StateAggregator(self.state)
        self.frames.addObserver(self.stateAggregator)

    def getState(self):
        self.streamData.append(self.connection.listen())
        return self.state.getDict()