from collections.abc import Iterable
from functools import reduce
import json
import re
import struct




class Payload:
    def __init__(self, body):
        self.status = {}
        self.body = body

        # self.dumpBody()

    def dump(self):
        if len(self.status) > 0:
            print(json.dumps(self.status))
        else:
            self.dumpBody()
    
    def dumpBody(self):
        print(' '.join(f'{b:02X}' for b in self.body))


    def getStatus(self):
        # if len(self.status) > 0:
        #     self.dump()
        return self.status

#
# lots of payload cracking things taken from
#   https://docs.google.com/document/d/1M0KMfXfvbszKeqzu6MUF_7yM6KDHk8cZ5nrH1_OUcAc/edit
#

class DatePayload(Payload):
    DAY = { 0x01: "Sunday",
            0x02: "Monday",
            0x04: "Tuesday",
            0x08: "Wednesday",
            0x10: "Thursday",
            0x20: "Friday",
            0x40: "Saturday" }

    def __init__(self, body):
        super().__init__(body)

        try:
            self.status['hour'] = self.body[0]
            self.status['min'] = self.body[1]
            # dow is a bit shift 0x01 << <ordinal DOW - Sun == 0, Sat == 6)
            self.status['dow'] = self.DAY[self.body[2]]
            self.status['day'] = self.body[3]
            self.status['month'] = self.body[4]
            self.status['year'] = self.body[5]
            self.status['adjust'] = self.body[6]
            self.status['dst'] = self.body[7]
        except Exception as err:
            pass


class StatusPayload(Payload):
    # circuit bit-masks for byte 2
    SPA     = 0x01
    AUX1    = 0x02
    AUX2    = 0x04
    AUX3    = 0x08
    POOL    = 0x20
    FEATURE1 = 0x10
    FEATURE2 = 0x40 
    FEATURE3 = 0x80
    # byte 3
    FEATURE4 = 0x01

    # modes for byte 9
    RUN_MODE    = 0x01 # Run Mode (Normal/Service)
    TEMP_UNITS  = 0x04 # Temp Unit (F/C),
    FREEZE_PROTECT = 0x08 # Freeze Protection (Off/On)
    TIMEOUT     = 0x10 # Timeout (Off/On)

    # byte 10
    #HEATER_ON  = 0x0F
    HEATER_ON = 0x0C    # can't find this doc'd anywhere... but mine seems to be 0x0C
    # HEATER_OFF = 0x03 # seems to be wrong... off is off 0x00

    # byte 12
    DELAY = 0x04

    # byte 22 -- masks -- pool is low nibble, spa is high nibble (realy low 2 bits of high nibble)
    # Actually... seems to be just low nibble... high 2 bits for spa, low 2 bits for pool
    HEATER_POOL_OFF     = 0x00  
    HEATER_POOL_EN      = 0x01
    HEATER_POOL_SOLAR_PREF = 0x02
    HEATER_POOL_SOLAR_EN = 0x03

    HEATER_SPA_OFF      = 0x00
    HEATER_SPA_EN       = 0x10

    def __init__(self, body):
        super().__init__(body)

        try:
            self.status['hour'] = self.body[0]
            self.status['min'] = self.body[1]

            self.status['spa'] = (self.body[2] & self.SPA) != 0
            self.status['aux1'] = (self.body[2] & self.AUX1) != 0
            self.status['aux2'] = (self.body[2] & self.AUX2) != 0
            self.status['aux3'] = (self.body[2] & self.AUX3) != 0
            self.status['pool'] = (self.body[2] & self.POOL) != 0
            self.status['feature1'] = (self.body[2] & self.FEATURE1) != 0
            self.status['feature2'] = (self.body[2] & self.FEATURE2) != 0
            self.status['feature3'] = (self.body[2] & self.FEATURE3) != 0

            self.status['feature4'] = (self.body[3] & self.FEATURE4) != 0

            # byte 4 - 8 are 0
            if reduce((lambda x, sum: sum + x), self.body[4:8]) != 0:
                print('unusual bytes 4 - 8 in StatusPayload')

            self.status['runMode'] = self.body[9] & self.RUN_MODE
            self.status['tempUnits'] = self.body[9] & self.TEMP_UNITS
            self.status['freezeProtect'] = self.body[9] & self.FREEZE_PROTECT            
            self.status['timeout'] = self.body[9] & self.TIMEOUT

            # if body[10] != self.HEATER_OFF and body[10] != self.HEATER_ON:
            #     print(f'unusual heater setting in StatusPayload {body[10]:02X}')
            self.status['heater'] = (self.body[10] == self.HEATER_ON)

            if self.body[11] != 0:
                print('unusual byte 11 in StatusPayload')
            
            # if (body[12] & 0x30) != 0x30:
            #     print(f'unusual byte 12 in StatusPayload {body[12]:02X}')
            self.status['delay'] = (self.body[12] & self.DELAY) != 0

            self.status['waterTemp'] = self.body[14] # repeated in body[15]
            self.status['spaTemp'] = self.body[15]
            self.status['airTemp'] = self.body[18]
            self.status['solarTemp'] = self.body[19]

            self.status['poolHeaterMode'] = (self.body[22] & 0x03)
            self.status['spaHeaterMode'] = ((self.body[22] & 0x0C) >> 2)
        
        except Exception as err:
            pass


class PumpPayload(Payload):
    # sample:  
    # 00,10,60,07,0F,0A 02 02 03 11 09 60 00 00 00 00 00 01 13 3B
    def __init__(self, body):
        super().__init__(body)
        try:
            self.status['pumpStarted'] = (self.body[0] & 0x0A) != 0

            (self.status['pumpMode'],
            self.status['pumpState'],
            self.status['pumpWatts'],
            self.status['pumpRPM'] ) = struct.unpack(">BBHHxx", self.body[1:9])

            # print(f"read RPM {self.status['pumpRPM']} from:"); self.dumpBody()

            # there are a lot more bytes... seem to be sequence number...
        except Exception as err:
            pass


class PingPayload(Payload):
    # think this is just a ping to see if the other party is alive
    def __init__(self, body):
        super().__init__(body)
        try:
            if self.body[0] != 0xFF:
                print(f'unkown ping data: {body[0]:02X}')
        except Exception as err:
            pass

    def dump(self):
        pass

class PumpStatus(Payload):
    PUMP_STARTED = 0x0A
    PUMP_STOPPED = 0x04

    def __init__(self, body):
        super().__init__(body)

        try:
            self.status['pumpStarted'] = (self.body[0] & 0x0A) != 0
        except Exception as err:
            pass

class CommandPayload(Payload):
    def __init__(self, body):
        super().__init__(body)
        # print("Command Payload")
        self.dumpBody()

        try:
            # (self.status['pumpRPM'],) = struct.unpack(">H", self.body[-2:])
            # print(f"read RPM {self.status['pumpRPM']} from:"); self.dumpBody()
            pass
        except Exception as err:
            pass

# 24,0F,10,08,0D,4C 4C 3D 55 64 00 00 00 00 00 00 00 00
# temperatures: water water air water-set spa-set
class TempPayload(Payload):
    def __init__(self, body):
        super().__init__(body)

        try:
            # 8 unused bytes... probably solar and other features I don't have
            (self.status['waterTemp'],
            self.status['spaTemp'],
            self.status['airTemp'],
            self.status['poolSetTemp'],
            self.status['spaSetTemp']) = struct.unpack("bbbbbxxxxxxxx", self.body)

        except Exception as err:
            pass

#
# A Command
#
class Command:
    def __init__(self, dst, cmd, commandType=0x24, src=0x21):
        self.type = commandType
        self.destination = dst
        self.source = src
        self.command = cmd

        self.payload = b''

    def getParsedCommand(self):
        parsed = {}
        parsed['type'] = self.type
        parsed['destination'] = self.destination
        parsed['source'] = self.source
        parsed['command'] = self.command

        parsed['payloadLength'] = len(self.payload)
        parsed['payload'] = self.payload

        # parsed['state'] = self.parsePayloadFromFrame(parsed)

        return parsed

# 0x86 - Turn Circuits On and Off 
#
# example:
#   24	10	20	86	2	06 01
#
# will be followed with a ACK from the dest
#
class CircuitChangeCommand(Command):
    CKT_SELECTORS = {
        'spa': 0x01, 
        'aux1': 0x02, 
        'aux2': 0x03, 
        'aux3': 0x04, 
        'feature1': 0x05,         
        'pool': 0x06, 
        'feature2': 0x07, 
        'feature3': 0x08, 
        'feature4': 0x09,
        'HEAT_BOOST': 0x85
    }

    def __init__(self, ckt, onOff, dst=0x10):
        super().__init__(dst, 0x86)

        try:
            circuit = self.CKT_SELECTORS[ckt].to_bytes(1, 'big')
            state = b'\x01' if onOff else b'\x00'

            self.payload = circuit + state
        except Exception as e:
            pass

# 0x88 - Change heating parameters -- set points, enable
#
# example:
#   24	10	20	88	4	52 64 05 00
#
class HeatChangeCommand(Command):
    # modes
    OFF = 0x00
    HEATER = 0x01
    SOLAR = 0x02
    SOLAR_PREF = 0x03

    def __init__(self, poolSet, spaSet, spaMode, poolMode, dst=0x10):
        super().__init__(dst, 0x88)

        mode = (spaMode << 2) | poolMode

        self.payload =  poolSet.to_bytes(1, byteorder='big') + \
                        spaSet.to_bytes(1, byteorder='big') + \
                        mode.to_bytes(1, byteorder='big') + \
                        b'\x00'
        pass


class PentairProtocol:
    RECORD_SEPARATOR = b'\xFF\x00\xFF'
    IDLE_BYTE = b'\xFF'
    START_BYTE = 0xA5

    def __init__(self):
        self.payloads = {
            0x00: { #0x01: CommandPayload,  # this is really an ACKnowledgement of the cmd in the payload
                    #0x04: PingPayload,
                    #0x06: PumpStatus,
                    0x07: PumpPayload },
            0x24: { 0x02: StatusPayload,
                    0x05: DatePayload,
                    0x08: TempPayload }
        }

        self.commandPayloads = {
            'spa': CircuitChangeCommand, 
            'aux1': CircuitChangeCommand, 
            'aux2': CircuitChangeCommand, 
            'aux3': CircuitChangeCommand, 
            'pool': CircuitChangeCommand, 
            'feature1': CircuitChangeCommand, 
            'feature2': CircuitChangeCommand, 
            'feature3': CircuitChangeCommand, 
            'feature4': CircuitChangeCommand
        }
            # 'CircuitChanges': {
            #     'command': CircuitChangeCommand,
            #     'selectors': [ "spa", "aux1", "aux2", "aux3", "pool", "feature1", "feature2", "feature3", "feature4" ]
            # },
            # 'HeatChanges': {
            #     'command': HeatChangeCommand,
            #     'selectors': [ "poolSetTemp", "spaSetTemp", "poolHeaterMode", "spaHeaterMode" ]
            # }

        # "airTemp", "solarTemp", "runMode","tempUnits", "freezeProtect", "timeout", "heater", "delay"
        # "pumpStarted","pumpMode", "pumpState", "pumpWatts", "pumpRPM", "waterTemp", "spaTemp"


        self.resetStats()

    def getStats(self):
        return self.stats

    def resetStats(self):
        self.stats= {   'frameCount': 0,
                        'badFrames': 0,
                        'unprocessedPayloads': 0 }

    # computes checksum for a frame 
    #   if using an incoming frame, strip off the checksum before calling -- e..g f[:-2]
    # otherwise, frame should include the START_BYTE and otherwise be stripped from IDLE_BYTES
    def checkSum(self, frame):
        cs = reduce((lambda x, sum: sum + x), frame)
        return cs

    #
    # validFrame
    #
    #   returns validity of the unpadded frame (that is, remove padding before calling)
    #
    #   A frame has:
    #       START_BYTE      1 bytes -- but this is stripped...
    #       version         1 bytes
    #       data            0+ bytes
    #       checksum        2 bytes Big Endian
    #
    #   frame is validated to have this structure and checksum calculated on frame [:-2]
    #   that is... the full frame less the check sum.  The checksum is the sum of START, version,
    #   and all databytes modulo 2^16
    #
    def validFrame(self, f):
        try:
            f = f.rstrip(self.IDLE_BYTE)
            # valid = f[0] == self.START_BYTE and ((f[-2] << 8) + f[-1]) & 0xFFFF == reduce((lambda x, sum: sum + x), f[:-2])
            valid = f[0] == self.START_BYTE and ((f[-2] << 8) + f[-1]) & 0xFFFF == self.checkSum(f[:-2])
            
            # increment badFrame counter for checksum errors ONLY... not for 'empty' frames
            self.stats['badFrames'] += not valid
        except Exception as e:
            valid = False

        return valid

    #
    #   parsePayloadFromFrame
    #
    def parsePayloadFromFrame(self, frame):
        state = {}

        try:
            if frame['payloadLength'] != len(frame['payload']):
                raise Exception                         

            payload = self.payloads[frame['type']][frame['command']](frame['payload'])
            # self.state.update(payload.getStatus())       # just overwrite ... and get the latest
            state = payload.getStatus()
            # payload.dump()

        except Exception as err:
            self.stats['unprocessedPayloads'] += 1
            # print(err)
        #     print(",".join(list(map((lambda x: f'{x:02X}' if not isinstance(x, Iterable) else ' '.join(f'{b:02X}' for b in x) if len(x) > 0  else ''), list(frame.values())))))
                
        return state


    #
    #   parseFrame
    #
    #   returns a dict with the parsed components of the frame 
    #   DOES NOT PARSE PAYLOAD or SPECIFIC MESSAGE CODES
    #
    def parseFrame(self, f):
        self.stats['frameCount'] += 1
        f = f.rstrip(self.IDLE_BYTE)

        if not self.validFrame(f):
            return {}

        parsed = {}
        try:
            parsed['type'] = f[1]
            parsed['destination'] = f[2]
            parsed['source'] = f[3]
            parsed['command'] = f[4]

            parsed['payloadLength'] = f[5]
            parsed['payload'] = f[6:-2]

            parsed['state'] = self.parsePayloadFromFrame(parsed)

        except Exception as e:
            pass

        return parsed

    # commands are dicts with fields separated out -- just as if parsed
    def createCommand(self, desiredState):
        cmd = {}

        try:
            k = list(desiredState.keys())[0]
            command = self.commandPayloads[k](k, desiredState[k])

            cmd = command.getParsedCommand()

        except Exception as e:
            pass

        return cmd

    def createFrame(self, command):
        frame = self.RECORD_SEPARATOR + self.START_BYTE + self.RECORD_SEPARATOR

        try:
            frame  = b''.join(list(map( lambda x: x.to_bytes(1, 'big'),[    
                self.START_BYTE,           
                command['type'],
                command['destination'],
                command['source'],
                command['command'],
                command['payloadLength']
            ] ))) + command['payload'] # payload is already serialized

            check = self.checkSum(frame)

            frame = self.RECORD_SEPARATOR + frame + check.to_bytes(2, 'big') + self.RECORD_SEPARATOR
        
        except Exception as e:
            pass

        return frame

