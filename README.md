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
or
```
pentair-control.py -c True -t 0.1 -i dump.raw
````

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
| 20 | wireless remote |
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

### some observed messages

```
type,dest,src,code,len,payload,Comment
24,0F,10,2,1D,0C 2E 20 00 00 00 00 00 00 20 00 00 20 86 53 53 00 00 66 00 00 00 00 00 00 CB A5 00 0D,look at 3rd byte - 20 - pool (20) is on
```
this was the first 'status' message of a capture run.  I used the remote to turn on the cleaner (sweep)  with this message

```
24,10,20,86,2,02 01,from handheld (20) to controller (10) - circuit change req AUX1 (02) to ON (01) -- turn cleaner on
```
it has been noted to me that if you try to spoof this command with src of 0x20, it may fail.  that may be because of the ack:
```
24,20,10,1,1,86,from Controller (10) to handheld (20) - ack (payload 86) ckt change request (code 01)
```

Also of note is that the interpretation of AUX1 as the sweep boost pump is likely specific to my installation.  I would expect there are some 'delay' flags in between these commands and the actual activation.  And may need to ramp up the main pump's RPM...





and then got this status
```
24,0F,10,2,1D,0D 28 22 00 00 00 00 00 00 20 00 00 20 86 53 53 00 00 66 00 00 00 00 00 00 CB A5 00 0D,now in 3rd byte AUX 1 (02) is added to pool (20) being on -- sweep
```
Payload: `0D 28 22 00 00 00 00 00 00 20 00 00 20 86 53 53 00 00 66 00 00 00 00 00 00 CB A5 00 0D`

Decoding it


| BYTE | EXAMPLE | Value |
| ---- | ------| ------ |
| [0] | 0D | 24-hr time in hours  (0-23, decimal) - 0x0D = 13 or 1 PM |
| [1] | 28 | Time in minutes      (0-59, decimal) - 0x28 = 40
| [2] | 22 | Circuits that are on: |
| | |     When SPA is on,          0x01 (2^0) bit is set |
| | |     When AUX1 is on,         0x02 (2^1) bit is set |
| | |     When AUX2 is on,         0x04 (2^2) bit is set |
| | |     When AUX3 is on,         0x08 (2^3) bit is set |
| | |     When POOL is on,         0x20 (2^5) bit is set |
| | |     When FEATURE1 is on,     0x10 (2^4) bit is set |
| | |     When FEATURE2 is on,     0x40 (2^6) bit is set |
| | |     When FEATURE3 is on,     0x80 (2^7) bit is set |
| | |     If SPA and POOL bits are both set, spa runs (not pool). |
| | |           0x22 == AUX1 (sweepi) and 0x20 == POOL On |
| [3] | 00 |  Additional circuits that are on: |
| | |     When FEATURE4 is on,     0x01 (2^0) bit is set |
| [4-8] | 00 00 00 00 00 | All zero (Additional circuit bitmasks on fancier controllers) |
| [9] | 20 |  Mode mask: 0x01 - Run Mode (Normal/Service), 0x04 - Temp Unit (F/C), |
| | |     0x08 - Freeze Protection (Off/On), 0x10 - Timeout (Off/On).  |
| | |   0x20 == ??? -- dunno... seems to always be 20
| [10] | 00 |  0x0f if heater is on; 0x03 if heater is off |
| [11] | 00 | Zero |
| [12] | 20 |  0x4 (2^2) bit indicates DELAY on AUX2 (and perhaps other circuits). |
| | |     Bits 0x30 appears to be on all the time. Don’t know why. |
| | | on my system.. this always seem to be 20 |
| [13] | 86 | 0x08 (on 1.0 fw); 0x00 or 0x01 on 2.070 FW.; mine alwyas seems to be 0x86 |
| [14] | 53 | POOL Water Temperature (degrees, only meaningful when circulating) - 0x53 == 86 deg F
| | |   see Mode Mask - byte [9], bit mask 0x04... but maybe that's wrong |
| [15] | |   SPA water temperature |
| [16] | 00 |  0x01 on 1.0 FW; 0x02 of 2.070 FW. Major version number? -- 0x00 on my unit |
| [17] | 00 | Zero on 1.0 FW 0x46 (= 70 decimal) on 2.070 FW. Minor version num? |
| [18] | 66 | Air Temperature (degrees) -- 0x66 == 102 deg F, yes... it was hot |
| [19] | 00 | Solar Temperature (degrees) -- 00 == i don't have solar |
| [20] | 00 | Zero |
| [21] | 00 | 0x32 (50 decimal) in 2.070 FW |
| [22] | 00 | Heat setting:  |
| | |     Low order 2 bits are pool: 0 off, 1 heater, 2 solar pref, 3 solar |
| | |     Next 2 bits are spa: 0 off, 4 htr, 8 solar pref, 12 solar |
| [23] | 00 | zero in 1.0 FW; 0x10 in 2.070 FW |
| [24] | 00 | All zero |
| [25] | CB | mystery |
| [26] | A5 | no clue |
| [27] | 00 | 0x19 / 0x38; 0x00 -- seems constant |
| [28] | 0D | 0x0A; 0x0B on 2.070 FW; in these captures 0x0D |

### Setup and Debugging

This is very specific to my setup, but it's worth documenting. As noted, I'm using a Raspberry Pi Zero W wired to the IntelliTouch controller via 4-wire EIA-485 and a Seeed Studio Grove 485 adapter. I'm developing and debugging using VS Code on a Mac on the same WiFi network -- about 80 feet away. VS Code has some cool remote debugging facilities, but I'm forwarding the serial port over a socket to the mac and debugging locally.

First, set up the 'listener' on the Mac with two windows or split panes in a iTerm2 session
```
# first session
nc -l 3000 >dumpXX.raw
```
could also use a named pipe, but I wanted to save the raw for replay & debug.
```
# second session -- optional, but helps keep an eye on things
tail -f dumpXX.raw | xxd -
```

That sets up the listener. Now set up the sender/forwarder on the Pi. I like to do it in 3 panes under tmux.
```
# first session
mkfifo pool

tail -f /dev/ttyS0 > pool
```
might also want to turn the terminal bell OFF in this session.
```
# second session

xxd pool
```
Not strictly necessary, but I like to see the hex scroll by on both sides. Then forward the traffic.  Need to match port numbers, 3000 is just an example.
```
# third session

cat pool | nc mini.local 3000
```


