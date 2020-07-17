#!/usr/bin/python3
from collections.abc import Iterable
from FileReader import FileReader
from Observer import *
from PentairProtocol import PentairProtocol
from SerialReader import SerialReader

import argparse
from datetime import datetime
import json
import logging
import time


# an observable chunk of raw data from the serial port, or a file, or ?
class ObservableString(Observable):
    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.chunk = b''

    # call to add to the end of the chunk, notifies observers
    def append(self, increment):
        if len(increment) > 0:
            self.chunk = self.chunk + increment

            self.notifyObservers(self.chunk)
            self.clear()

# an Observaable wrapped array
class ObservableArray(Observable):
    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.elements = []

    def append(self, newElements):
        if len(newElements) > 0:
            self.elements.extend(newElements)

            self.notifyObservers(self.elements)
            self.clear()

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

        # for m in messages:
        #     self.frames.append(self.protocol.parseFrame(m))

class CSVOutput(Observer):
    def __init__(self):
        super().__init__()

    def update(self, objects):
        for o in objects:
            if len(o) > 0:
                print( ",".join(list(map((lambda x: f'{x:02X}' if not isinstance(x, Iterable) else ' '.join(f'{b:02X}' for b in x) if len(x) > 0  else ''), list(o.values())))) )



# Configure logging
logger = logging.getLogger("Pentair-Thing.core")
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Read in command-line parameters
parser = argparse.ArgumentParser()

#
# Input Sources
#
# file input args
parser.add_argument("-i", "--inputfile", action="store", required=False, dest="inFile", default="", help="input file with raw protocol stream")

# serial port args
# parser.add_argument("-p", "--port", action="store", required=True, dest="port", default="/dev/ttyS0", help="Serial Port Device")
parser.add_argument("-t", "--timeout", action="store", required=True, dest="timeout", default="0.5", help="Timeout to wait for events")

#
# Output Options
#
# parser.add_argument("-c", "--csv", action="store", required=False, dest="csv", default=False, help="print every frame in csv, don't parse")
# mqtt publish...

args = parser.parse_args()
inFile = args.inFile
timeout = float(args.timeout)


'''
Reader -> streamData --> MessageParser -> messages -> FrameParser -> frames -> Output
'''

# streamData is an Observable to connect the raw stream from connection to downstream observers
streamData = ObservableString()
messages = ObservableArray()
frames = ObservableArray()

if len(inFile) > 0:
    print(f'using {inFile} as source')
    connection = FileReader(inFile)
else:
    port = args.port
    print(f'using {port} as source')
    connection = SerialReader(port)

    timeout = float(args.timeout)
# connection will read from either sourcse


# messageParser will chop the stream into separate messages
messageParser = MessageParser(PentairProtocol.RECORD_SEPARATOR, messages)
# connect messageParser as an oberver of streamData
streamData.addObserver(messageParser)

frameParser = FrameParser(frames)
messages.addObserver(frameParser)

output = CSVOutput()
frames.addObserver(output)



def do_something():
    if not connection.isOpen():
        connection.open()

    streamData.append(connection.listen())


def run():
    if not connection.isOpen():
        connection.open()

    while True:
        time.sleep(0.9*timeout)         # crude approach to timing adjustment
        do_something()

if __name__ == "__main__":

    # do_something(connection, protocol)
    run()
