from collections.abc import Iterable
from functools import reduce
import json
import re
import struct


RECORD_SEPARATOR = b'\xFF\x00\xFF'


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
        return self.status

#
# lots of payload cracking things taken from
#   https://docs.google.com/document/d/1M0KMfXfvbszKeqzu6MUF_7yM6KDHk8cZ5nrH1_OUcAc/edit
#

class DatePayload(Payload):
    def __init__(self, body):
        super().__init__(body)

        try:
            self.status['hour'] = self.body[0]
            self.status['min'] = self.body[1]
            self.status['dow'] = self.body[2]
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
    HEATER_ON  = 0x0F
    # HEATER_OFF = 0x03 # seems to be wrong... off is off 0x00

    # byte 12
    DELAY = 0x04

    # byte 22 -- masks -- pool is low nibble, spa is high nibble (realy low 2 bits of high nibble)
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
            self.status['delay'] = self.body[12] & self.DELAY

            self.status['waterTemp'] = self.body[14] # repeated in body[15]
            self.status['waterTemp2'] = self.body[15]
            self.status['airTemp'] = self.body[18]
            self.status['solarTemp'] = self.body[19]

            self.status['poolHeaterMode'] = self.body[22] & 0x0F
            self.status['spaHeaterMode'] = self.body[22] & 0xF0
        
        except Exception as err:
            pass


class PumpPayload(Payload):
    # sample:  0A 02 02    03 03    09 60    00 00 00 00 00 01 00 0F
    def __init__(self, body):
        super().__init__(body)
        try:
            self.status['pumpStarted'] = (self.body[0] & 0x0A) != 0

            (self.status['pumpMode'],
            self.status['pumpState'],
            self.status['pumpWatts'],
            self.status['pumpRPM'] ) = struct.unpack(">BBHH", self.body[1:9])

            print(f"read RPM {self.status['pumpRPM']} from:"); self.dumpBody()

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
        print("Command Payload")
        self.dumpBody()

        try:
            (self.status['pumpRPM'],) = struct.unpack(">H", self.body[-2:])
            print(f"read RPM {self.status['pumpRPM']} from:"); self.dumpBody()

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
            self.status['waterTemp2'],
            self.status['airTemp'],
            self.status['poolSetTemp'],
            self.status['spaSetTemp']) = struct.unpack("bbbbbxxxxxxxx", self.body)

        except Exception as err:
            pass


class PentairProtocol:
    IDLE_BYTE = b'\xFF'
    START_BYTE = 0xA5

    def __init__(self):
        self.payloads = {
            0x00: { 0x01: CommandPayload,
                    0x04: PingPayload,
                    0x06: PumpStatus,
                    0x07: PumpPayload },
            0x24: { 0x02: StatusPayload,
                    0x05: DatePayload,
                    0x08: TempPayload }
        }

        self.state = {}
 
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
            valid = f[0] == self.START_BYTE and ((f[-2] << 8) + f[-1]) & 0xFFFF == reduce((lambda x, sum: sum + x), f[:-2])
            # valid = ((f[-2] << 8) + f[-1]) & 0xFFFF == reduce((lambda x, sum: sum + x), f[:-2], 0xA5)
            
        except Exception as e:
            valid = False

        return valid

    #
    #   parseFrame
    #
    #   returns a dict with the parsed components of the frame 
    #   DOES NOT PARSE PAYLOAD or SPECIFIC MESSAGE CODES
    #
    def parseFrame(self, f):
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

        except Exception as e:
            pass

        return parsed
    

    def parseEvents(self, events):
        while events:
            e = events[0].rstrip(self.IDLE_BYTE)
            # print(e)

            if self.validFrame(e):
                frame = self.parseFrame(e)

                try:
                    if frame['payloadLength'] != len(frame['payload']):
                        raise Exception                         

                    payload = self.payloads[frame['type']][frame['command']](frame['payload'])
                    self.state.update(payload.getStatus())       # just overwrite ... and get the latest
                    # payload.dump()

                except Exception as err:
                    # print(err)
                    print(",".join(list(map((lambda x: f'{x:02X}' if not isinstance(x, Iterable) else ' '.join(f'{b:02X}' for b in x) if len(x) > 0  else ''), list(frame.values())))))
                    pass

            events = events[1:]

        return self.state
