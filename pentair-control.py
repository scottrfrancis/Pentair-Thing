#!/usr/bin/python3
from collections.abc import Iterable
from distutils.util import strtobool
from FileReader import FileReader
from GreengrassAwareConnection import *
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


class StateAggregator(Observer):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def update(self, parsedFrames):
        for p in parsedFrames:
            if 'state' in p:
                self.state.append(p['state'])

class MQTTPublisher(Observer):
    def __init__(self, client, topic):
        super().__init__()
        self.client = client
        self.topicBase = topic

    def update(self, parsedFrames):
        for p in parsedFrames:
            try:
                topic = self.topicBase + '/' + \
                    "/".join((str(p['type']), str(p['destination']), str(p['source']), str(p['command'])))
                message = " ".join(f'{b:02X}' for b in p['payload'])
                self.client.publishMessageOnTopic(message, topic)
            except KeyError as e:
                pass

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

parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
parser.add_argument("-n", "--thingName", action="store", dest="thingName", default="Bot", help="Targeted thing name")

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
parser.add_argument("--csv", action="store_true", help="print every frame in csv, append parsed")
# mqtt publish...
parser.add_argument("--raw", action="store_true", help="publish raw payloads on parsed topics")

args = parser.parse_args()
host = args.host
rootCA = args.rootCAPath
cert = args.certificatePath
key = args.privateKeyPath
thingName = args.thingName

inFile = args.inFile
timeout = float(args.timeout)
csv = args.csv


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
stateAggregator = StateAggregator(state)
frames.addObserver(stateAggregator)

if csv:
    output = CSVOutput()
    frames.addObserver(output)

try:
    iotConnection = GreengrassAwareConnection(host, rootCA, cert, key, thingName)

    # iotConnection.deleteShadow()
except Exception as e:
    logger.error(f'{str(type(e))} Error')

if args.raw:
    publisher = MQTTPublisher(iotConnection, thingName + "/raw")
    frames.addObserver(publisher)


def do_something(last_update = {}):
    if not connection.isOpen():
        connection.open()

    streamData.append(connection.listen())

    accState = state.getDict()
    for k in ['hour', 'min', 'dow', 'day', 'month', 'year', 'adjust', 'dst']:
        if k in accState:
            accState.pop(k)

    if accState != last_update:
        stateMessage = json.dumps(accState)
        logger.info(stateMessage)
        iotConnection.updateShadow(accState)
        last_update = accState
    # iotConnection.publishMessageOnTopic(stateMessage, thingName + '/t')

    stats = json.dumps(protocol.getStats())
    logger.info(stats + "\n")
    iotConnection.publishMessageOnTopic(stats, thingName + '/s')
    
    protocol.resetStats()

    return last_update

def run():
    if not connection.isOpen():
        connection.open()

    last_update = {}
    while True:
        time.sleep(0.9*timeout)         # crude approach to timing adjustment
        last_update = do_something(last_update)

if __name__ == "__main__":

    # do_something(connection, protocol)
    run()
