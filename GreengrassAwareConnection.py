# GreengrassAwareConnection.py
#
#   class to connect to IoT core or gg based on discovery.
# methods to publish to topic, subscribe, shadow, etc.
#
#   Based on v 1 of the Python SKD
#

import logging
import os
import uuid

from AWSIoTPythonSDK.core.greengrass.discovery.providers import DiscoveryInfoProvider
from AWSIoTPythonSDK.core.protocol.connection.cores import ProgressiveBackOffCore
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.exception.AWSIoTExceptions import DiscoveryInvalidRequestException



class GreengrassAwareConnection:
    MAX_DISCOVERY_RETRIES = 10
    GROUP_CA_PATH = "./groupCA"

    def __init__(self, host, rootCA, cert, key, thingName):
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

        self.backOffCore = ProgressiveBackOffCore()

        self.discovered = False
        self.discoverBroker()

        self.connected = False
        self.connect()

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
                print("Error message: %s" % e.message)
                retryCount -= 1
                print("\n%d/%d retries left\n" % (retryCount, MAX_DISCOVERY_RETRIES))
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

                break
            except BaseException as e:
                self.logger.warn("Error in Connect: Type: %s" % str(type(e)))

    def publishMessageOnTopic(self, message, topic, qos=0):
        if not self.isConnected():
            raise ConnectionError()

        return self.client.publish(topic, message, qos)