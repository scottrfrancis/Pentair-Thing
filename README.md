# Pentair-Thing

A rudimentary AWS IoT Thing implementation for a Pentair EasyTouch controller.

While this project targets AWS IoT / Greengrass integration, the components should be modular enough to help anyone else integrate with other automation systems and to serve as a platform for decoding Pentair protocol for additional equipment.

* Current Status: Framework for capturing messages on the 485 bus and decoding payloads works. Payload decoders built for most common messages I see on my system 
Useful for understanding and decoding live protocol or collecting traffic samples.

_TODO_
1. Integrate latest AWS IoT Device SDK to publish messages to Greengrass (this will also facilitate debug)
2. Migrate protocol decoding to Greengrass Lambdas
3. Build coherent model for 'the pool' from collected messages and maintain model in Device Shadow
4. Implement commands: SPA On, Pool On, All Off, Heat Pool, Heat Spa, Heat Off

### Purpose

To facilitate monitoring and control of residential pool equipment using the Pentair EasyTouch controller

### Background / Context

I have an EasyTouch controller, a Variable Speed Pump, a Booster pump for the sweep, a Jet pump for the spa, two controlled valves (to switch between pool and spa), and a gas Heater. The controller is mounted outside near the equipment, but I mostly interract with the equipment using the EasyTouch wireless remote. Equipment was installed around 2010, so there may be more modern versions. I don't have Solar heating, water features, or poly-chromic lighting--so the project won't have info about those systems, but should help someone discover the protocol for those.

The EasyTouch remote UX is extremely clunky. To do simple things are many menus deep with cryptic select/menu key sequences. My family has had a very hard time working with this system. This project supports an overall goal to make monitoring and control of the equipment more friendly and predictable by extending status and control through AWS IoT Core, a mobile app, and an Alexa skill to enable control of the system by phone, web, or voice.

### Integration Points

The EasyTouch wireless remote interfaces to the controller with a wireless transceiver. The transceiver connects to the controller over a 4 wire EIA-485 interface. This interface (485) also seems to be used for the pump and other machines, although EIA-232 direct links also seem to be used. Pentair does not publish any API, SDK, HDK, or other developer information that is available to customers. In fact, I couldn't even find any pay-for or partner resources either.

Some people have been successful in creating interfaces for their own purposes and a few have been gracious enough to post this information publicly. Here are some links to the resources I've found helpful in building this project:

* [Pentair EasyTouch Installation Guide](https://www.pentair.com/content/dam/extranet/aquatics/residential-pool/owners-manuals/automation/easytouch/easytouch-control-system-pl4-psl4-installation-guide.pdf)
* [SD Young's work to decode the protocol](https://web.archive.org/web/20171130091506/https:/www.sdyoung.com/home/decoding-the-pentair-easytouch-rs-485-protocol/)
* [Josh Block's notes on decoding](https://docs.google.com/document/d/1M0KMfXfvbszKeqzu6MUF_7yM6KDHk8cZ5nrH1_OUcAc/edit)

## Hardware Interface

For this project, I have connected a Raspberry Pi Zero Wireless to the EasyTouch Controller over a 4-wire EIA-485 link. The controller seems to source enough power at 15V DC to power the Pi using a [buck converter](https://docs.google.com/document/d/1M0KMfXfvbszKeqzu6MUF_7yM6KDHk8cZ5nrH1_OUcAc/edit). The 'A' and 'B' signals are decoded with an [EIA-485 Transceiver Module](https://wiki.seeedstudio.com/Grove-RS485/) and routed to UART0 on the Pi. All the wiring is done on a [proto board](https://www.adafruit.com/product/571?gclid=Cj0KCQjwo6D4BRDgARIsAA6uN18kixfuLTQC-J3qJR--7Gl3GOsgvus298pjwGht9j0Ftrn9X5r5PccaApFrEALw_wcB) and a pi-standard 40-pin ribbon cable. All of this is mounted in an [IP66 Case](https://www.amazon.com/gp/product/B077QM9VM9/ref=ppx_yo_dt_b_asin_title_o03_s00?ie=UTF8&psc=1) and connected to the controller over standard sprinkler wire.

My house uses an [eero mesh wifi network](https://www.amazon.com/gp/product/B07WMLPSRL/ref=ppx_yo_dt_b_asin_title_o00_s00?ie=UTF8&psc=1) which provides good coverage for Pi, mounted near the controller.

_NOTE_: It is necessary to enable the Serial port on the Pi and for the serial port to NOT be login shell.  This is accomplished with the `raspi-config` tool. No other special configuration of the Pi was needed beyond current (2020-05-29) version of Pi OS (or Raspbian or whatever they call it this week).

## the code

`pentair-control.py` is the main entry point. It sets up user options, the Serial interface, and the protocol decoder.  It is intended to be run from a command similar to
```
pentair-control.py -p /dev/ttyS0 -t 60
```

The serial port is read by `PentairSerial.py` and splits the read buffer into 'events' or 'records' using a configurable record separator. 

`PentairProtocol.py` defines this separator and decodes the framing and payload.

### Decoding the Protocol

EIA-485 is designed as a multi-drop loop with no dedicated clock line. This means that devices must agree on datarate (baud rate). When no message is being broadcast (and since it's a common pair of wires, it's all broadcast), bytes are read as `0xFF` by the serial port.  This means that there is *ALWAYS* something to read from the serial port.

In 485 protocols, there is typically a 'start' signal to indicate something useful is coming. In the Pentair implementation, this indicated by two consecutive bytes of `0x00` and then `0xFF`. Thus the 'record separator' is `0xFF 0x00 0xFF` where there could be a long string of `0xFF` preceding the separator. When these records are split, there will likely be many 'idle bytes' of `0xFF` at the end of each record. `PentairProtocol` strips these off the end. 

Events are interpreted as frames inside `PentairProtocol` according to a definition that has been emperically determined by the above resources, with a bit of my own sleuthing. The raw serial would look something like:
```
FFFFFFFFFF00FFA5001060010960FFFFFF
```
One way to loook at the raw payload is to use picocom and `xxd`.
```
mkfifo apipe
picocom -b 9600 /dev/ttyS0 -l | tee apipe 
```
in a second terminal:
```
xxd apipe
```
Note the long sequence of IDLE BYTES before and after this short message.  If the bytes come up inverted from this, you likely have the 'A' and 'B' connections reveresed. Either reverse them, or modify the code to invert all the bits.

Frames seem to be

| Field | example bytes | definition |
| ------- | ---------- | ---------- |
| IDLE BYTES+ | FFFF... | any number |
| START | 00FF | this ends the record separator |
| FRAME_START | A5 | included in checksum for frame. bit pattern ensure proper data rate |
| TYPE | [00,24] | some people also see 01.  could indicate versions or other protocols |
| DST | [0F, 10, 60,...] | address of intended recipient |
| SRC | [10, 60, ...] | address of sender |
| CMD | [01, 03, 08,...] | could also be considered as message id |
| LEN | 0D | length of payload |
| PAYLOAD | XX | LEN number of bytes |
| CHECKSUM | XXXX | two byte modulo sum of all bytes from FRAME_START (inclusive) through all of PAYLOAD |
| IDLE_BYTES+ | FFFF... | not really part of the frame, but FFs will follow any framing |

Inside `PentairProtocol`, frames are validated (by checksup) and if succeeded, the payload is loaded. It is important to validate the Checksum first as this is shared bus and any device can assert at anytime -- causing collisions and garbled data.

PAYLOADs are interpreted based on the TYPE and CMD values.  Additionally, it may be valuable to track SRCs and DSTs or only use one side.

Some common addresses for DSTs and SRCs:
| ADDR | Device |
| ---- | ------ |
| 0F | broadcast?  that is... everyone should pay attention? |
| 10 | controller -- could probably MOSTLY just use message FROM this addr |
| 60 | pump | 

Some common TYPEs and CMDs
| TYPE | CMD | meaning |
| --- | ---- | ----- |
| 00 | 01 | command, or circuit change, or other modification -- sets pump speed and maybe valves or other? |
| 00 | 04 | seems to be some kind of heartbeat or ping from the controller to a device (usually the pump - 60) and then a matching response |
| 00 | 06 | pump status -- is it running/started (0A) or stopped (04) |
| 00 | 07 | pump data -- started, mode, watts, rpm, etc. |
| 24 | 02 | status -- the motherload of info... time, date, temps, lots of stuff |
| 24 | 05 | date -- current controller date, happens every 2s or so |
| 24 | 08 | temps -- air, water, preferred, solar, other temperatures |

Seems like device 10 is the only one sending TYPE 24s.  These may be the main informational messages. The TYPE 00 messages seem to occur in pairs SRC -> DST then a complementary 'ACK' messages from DST -> SRC.

### Interpreting Payloads
A Simple, polymorphic class structure is implemented where specific payloads are intpreted based on TYPE and CMD. To add new interpreters:
1. Sub-Class Payload
2. Call `super().__init__(body)` in `__init__()`
3. Use `struct` or other means to interpret the payload and set `self.status`

The `status` member dicts will be aggregated (updated) -- creating a simple 'state' that I intend to use for shadow updates.

### Debugging the Protocol

It can be handy to print various things as you debug the messages. There are some handy utilities to dump the payload as either the interpreted structure or the raw frame (formatted as hex). The exception block in `parseEvents()` is particularly useful as this will catch the 'unhandled' payloads.

It can also be handy to dump every frame, modifying the format to be CSV, and redirecting that data to a file for analysis with Excel or whatever.