#!/usr/bin/python3

# from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import PentairProtocol
import PentairSerial
# import Shadow

import argparse
from datetime import datetime
import json
import logging
import time

# remote debug harness -- unco
# import ptvsd
# import socket
# this_ip = (([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or [[(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["no IP found"])[0]
# ptvsd.enable_attach(address=(this_ip,3000), redirect_output=True)
# ptvsd.wait_for_attach()
# end debug harness


# Read in command-line parameters
parser = argparse.ArgumentParser()
# IOT args
# parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
# parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
# parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
# parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
# parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
#                     help="Use MQTT over WebSocket")
# parser.add_argument("-n", "--thingName", action="store", dest="thingName", default="Bot", help="Targeted thing name")

# serial port args
parser.add_argument("-p", "--port", action="store", required=True, dest="port", default="/dev/ttyS0", help="Serial Port Device")
parser.add_argument("-t", "--timeout", action="store", required=True, dest="timeout", default="0.5", help="Timeout to wait for events")
# parser.add_argument("-q", "--query", action="store", dest="query", default="['Mute','Power','Video','Volume']", help="Inital queries to kick things off")


args = parser.parse_args()
# host = args.host
# rootCAPath = args.rootCAPath
# certificatePath = args.certificatePath
# privateKeyPath = args.privateKeyPath
# useWebsocket = args.useWebsocket
# thingName = args.thingName
# clientId = args.thingName

port = args.port
timeout = float(args.timeout)
# query = eval(args.query)


# if args.useWebsocket and args.certificatePath and args.privateKeyPath:
#     parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
#     exit(2)

# if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
#     parser.error("Missing credentials for authentication.")
#     exit(2)

# Configure logging
logger = logging.getLogger("Pentair-Thing.core")
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# setup serial & protocol
connection = PentairSerial.PentairSerial(port, PentairProtocol.RECORD_SEPARATOR)
protocol = PentairProtocol.PentairProtocol()

def customShadowCallback_Update(payload, responseStatus, token):
    # payload is a JSON string ready to be parsed using json.loads(...)
    # in both Py2.x and Py3.x
    if responseStatus == "timeout":
        logger.debug("Update request " + token + " time out!")
    # if responseStatus == "accepted":
    #     payloadDict = json.loads(payload)
    #     print("~~~~~~~~~~~~~~~~~~~~~~~")
    #     print("Update request with token: " + token + " accepted!")
    #     print("payload: " + json.dumps(payloadDict)) #["state"]["desired"]["property"]))
    #     print("~~~~~~~~~~~~~~~~~~~~~~~\n\n")
    if responseStatus == "rejected":
        logger.debug("Update request " + token + " rejected!")

def customShadowCallback_Delta(payload, responseStatus, token):
    logger.debug("Received a delta message:")
    payloadDict = json.loads(payload)
    deltaMessage = json.dumps(payloadDict["state"])
    logger.debug(deltaMessage + "\n")

    commands = protocol.makeCommands(payloadDict["state"])
    logger.debug("\nbuilt commands: " + str(commands) + "\n")
    connection.send(commands)


# Init AWSIoTMQTTShadowClient
# myAWSIoTMQTTShadowClient = None
# if useWebsocket:
#     myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId, useWebsocket=True)
#     myAWSIoTMQTTShadowClient.configureEndpoint(host, 443)
#     myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath)
# else:
#     myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId)
#     myAWSIoTMQTTShadowClient.configureEndpoint(host, 8883)
#     myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTShadowClient configuration
# myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
# myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
# myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect to AWS IoT
# myAWSIoTMQTTShadowClient.connect()

# Create a deviceShadow with persistent subscription
# deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(thingName, True)

# Listen on deltas
# deviceShadowHandler.shadowRegisterDeltaCallback(customShadowCallback_Delta)

state = {}
def do_something():
    if not connection.isOpen():
        connection.open()

    # listen for status events
    events = connection.listen()
    state.update(protocol.parseEvents(events))
    logger.info( str(datetime.now()) + " - " + json.dumps(state) + "\n")

    #     try:
    #         deviceShadowHandler.shadowUpdate(Shadow.makeStatePayload("reported", state), customShadowCallback_Update, 5)
    #     except Exception as e:
    #         print(e)



def run():
    if not connection.isOpen():
        connection.open()

    while True:
        time.sleep(0.9*timeout)         # crude approach to timing adjustment
        do_something()

if __name__ == "__main__":

    # do_something(connection, protocol)
    run()
