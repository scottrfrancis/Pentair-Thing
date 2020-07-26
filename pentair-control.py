#!/usr/bin/python3
from collections.abc import Iterable
from distutils.util import strtobool
from FileReader import FileReader
from Observer import *
from PentairProtocol import PentairProtocol
from SerialReader import SerialReader

import argparse
from datetime import datetime
import json
import logging
import time


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
    def __init__(self, frames, protocol):
        super().__init__()
        self.protocol = protocol

        self.frames = frames

    def update(self, messages):
        self.frames.append(list(map(self.protocol.parseFrame, messages)))


class stateAggregator(Observer):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def update(self, parsedFrames):
        for p in parsedFrames:
            if 'state' in p:
                self.state.append(p['state'])


class CSVOutput(Observer):
    def __init__(self):
        super().__init__()

    def update(self, objects):
        for o in objects:
            if len(o) > 0:
                try:
                    s = ''
                    if 'state' in o:
                        s = o.pop('state')
                    print( ",".join(list(map((lambda x: f'{x:02X}' if not isinstance(x, Iterable) else ' '.join(f'{b:02X}' for b in x) if len(x) > 0  else ''), list(o.values())))) + "," + json.dumps(s) )
                except Exception as err:
                    print(err)


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
parser.add_argument("-p", "--port", action="store", required=False, dest="port", default="/dev/ttyS0", help="Serial Port Device")
parser.add_argument("-t", "--timeout", action="store", required=True, dest="timeout", default="0.5", help="Timeout to wait for events")


#
# Output Options
#
parser.add_argument("-c", "--csv", action="store", required=False, dest="csv", default='False', help="print every frame in csv, don't parse")
# mqtt publish...

args = parser.parse_args()
inFile = args.inFile
timeout = float(args.timeout)
csv = strtobool(args.csv)


'''
Reader -> streamData --> MessageParser -> messages -> FrameParser -> frames -> Output
'''

# streamData is an Observable to connect the raw stream from connection to downstream observers
streamData = ObservableString()
messages = ObservableArray()
frames = ObservableArray()
state = ObservableDict()


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

protocol = PentairProtocol()
frameParser = FrameParser(frames, protocol)
messages.addObserver(frameParser)

state = ObservableDict()
stateAggregator = stateAggregator(state)
frames.addObserver(stateAggregator)

if csv:
    output = CSVOutput()
    frames.addObserver(output)



def do_something():
    if not connection.isOpen():
        connection.open()

    # state.clear()
    streamData.append(connection.listen())
    logger.info(json.dumps(state.getDict()))
    logger.info(json.dumps(protocol.getStats()) + "\n")
    protocol.resetStats()

def run():
    if not connection.isOpen():
        connection.open()

    while True:
        time.sleep(0.9*timeout)         # crude approach to timing adjustment
        do_something()

if __name__ == "__main__":

    # do_something(connection, protocol)
    run()
