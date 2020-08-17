# GreengrassAwareConnection.py
#
#   class to connect to IoT core or gg based on discovery.
# methods to publish to topic, subscribe, shadow, etc.
#
#   Based on v 1 of the Python SKD
#

import json
import logging
import os
import uuid

from AWSIoTPythonSDK.core.greengrass.discovery.providers import DiscoveryInfoProvider
from AWSIoTPythonSDK.core.protocol.connection.cores import ProgressiveBackOffCore
from AWSIoTPythonSDK.exception.AWSIoTExceptions import DiscoveryInvalidRequestException

from AWSIoTPythonSDK.MQTTLib import *


def shadowUpdate_callback(payload, responseStatus, token):
    if responseStatus != 'accepted':
        print(f"\n Update Status: {responseStatus}")
        print(json.dumps(payload))
        print("\n")

def shadowDelete_callback(payload, responseStatus, token):
    print(json.dumps({'payload': payload, 'responseStatus': responseStatus, 'token':token}))


class GreengrassAwareConnection:
    MAX_DISCOVERY_RETRIES = 10
    GROUP_CA_PATH = "./groupCA/"
    OFFLINE_QUEUE_DEPTH = 100

    def __init__(self, host, rootCA, cert, key, thingName, stateChangeQueue = None):
        self.logger = logging.getLogger("GreengrassAwareConnection")
        self.logger.setLevel(logging.DEBUG)
        streamHandler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        streamHandler.setFormatter(formatter)
        self.logger.addHandler(streamHandler)

        self.host = host
        self.rootCA = rootCA
        self.cert = cert
        self.key = key
        self.thingName = thingName

        self.stateChangeQueue = stateChangeQueue

        self.backOffCore = ProgressiveBackOffCore()

        self.discovered = False
        self.discoverBroker()

        self.connected = False
        self.connect()

        self.shadowConnected = False
        self.connectShadow()

    def hasDiscovered(self):
        return self.discovered


    def discoverBroker(self):
        if self.hasDiscovered():
            return
        
        # Discover GGCs
        discoveryInfoProvider = DiscoveryInfoProvider()
        discoveryInfoProvider.configureEndpoint(self.host)
        discoveryInfoProvider.configureCredentials(self.rootCA, self.cert, self.key)
        discoveryInfoProvider.configureTimeout(10)  # 10 sec

        retryCount = self.MAX_DISCOVERY_RETRIES
        self.groupCA = None
        coreInfo = None

        while retryCount != 0:
            try:
                discoveryInfo = discoveryInfoProvider.discover(self.thingName)
                caList = discoveryInfo.getAllCas()
                coreList = discoveryInfo.getAllCores()

                # We only pick the first ca and core info
                groupId, ca = caList[0]
                self.coreInfo = coreList[0]
                self.logger.info("Discovered GGC: %s from Group: %s" % (self.coreInfo.coreThingArn, groupId))

                self.groupCA = self.GROUP_CA_PATH + groupId + "_CA_" + str(uuid.uuid4()) + ".crt"
                if not os.path.exists(self.GROUP_CA_PATH):
                    os.makedirs(self.GROUP_CA_PATH)
                groupCAFile = open(self.groupCA, "w")
                groupCAFile.write(ca)
                groupCAFile.close()

                self.discovered = True
                break
            except DiscoveryInvalidRequestException as e:
                print("Invalid discovery request detected!")
                print("Type: %s" % str(type(e)))
                print("Error message: %s" % e.message)
                print("Stopping...")
                break
            except BaseException as e:
                print("Error in discovery!")
                print("Type: %s" % str(type(e)))
                # print("Error message: %s" % e.message)
                retryCount -= 1
                print("\n%d/%d retries left\n" % (retryCount, self.MAX_DISCOVERY_RETRIES))
                print("Backing off...\n")
                self.backOffCore.backOff()


    def isConnected(self):
        return self.connected

    def connect(self):
        if self.isConnected():
            return

        self.client = AWSIoTMQTTClient(self.thingName)
        self.client.configureCredentials(self.groupCA, self.key, self.cert)
        # myAWSIoTMQTTClient.onMessage = customOnMessage

        for connectivityInfo in self.coreInfo.connectivityInfoList:
            currentHost = connectivityInfo.host
            currentPort = connectivityInfo.port
            self.logger.info("Trying to connect to core at %s:%d" % (currentHost, currentPort))
            self.client.configureEndpoint(currentHost, currentPort)
            try:
                self.client.connect()
                self.connected = True

                self.currentHost = currentHost
                self.currentPort = currentPort
                break
            except BaseException as e:
                self.logger.warn("Error in Connect: Type: %s" % str(type(e)))

    def publishMessageOnTopic(self, message, topic, qos=0):
        if not self.isConnected():
            raise ConnectionError()

        return self.client.publish(topic, message, qos)

    def isShadowConnected(self):
        return self.shadowConnected

    def memberDeltaHandler(self, payload, responseStatus, token):
        print("\nReceived a Delta Message")

        payloadDict = json.loads(payload)
        state = payloadDict['state']
        deltaMessage = json.dumps(deltaMessage)
        print(deltaMessage + "\n")

        if self.stateChangeQueue != None:
            self.stateChangeQueue.append(state)



    def connectShadow(self):
        if not self.isConnected():
            self.logger.warn("connect regula client first to get host and port")
            raise ConnectionError

        self.shadowClient = AWSIoTMQTTShadowClient(self.thingName)
        self.shadowClient.configureEndpoint(self.currentHost, self.currentPort)
        self.shadowClient.configureCredentials(self.groupCA, self.key, self.cert)

        # AWSIoTMQTTShadowClient configuration
        self.shadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
        self.shadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
        self.shadowClient.configureMQTTOperationTimeout(5)  # 5 sec

        self.shadowClient._AWSIoTMQTTClient.configureOfflinePublishQueueing(self.OFFLINE_QUEUE_DEPTH, DROP_OLDEST)

        self.shadowClient.connect()

        # Create a deviceShadow with persistent subscription
        self.deviceShadowHandler = self.shadowClient.createShadowHandlerWithName(self.thingName, True)

        self.deviceShadowHandler.shadowRegisterDeltaCallback(self.memberDeltaHandler)

        self.shadowConnected = True

    
    def updateShadow(self, update):
        if not self.isShadowConnected():
            raise ConnectionError

        state = {'state': {
                    'reported': update
        }}
        self.deviceShadowHandler.shadowUpdate(json.dumps(state), shadowUpdate_callback, 10)



    def deleteShadow(self):
        if not self.isShadowConnected():
            raise ConnectionError

        self.deviceShadowHandler.shadowDelete(shadowDelete_callback, 5)
