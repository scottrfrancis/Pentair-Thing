# See https://web.archive.org/web/20171130091506/https:/www.sdyoung.com/home/decoding-the-pentair-easytouch-rs-485-protocol/
# For details on pentair protocol
#
import serial
from Connection import Connection


class SerialReader(Connection):
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.ser = serial.Serial(
            port=self.device,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS, timeout=0.1, write_timeout=0.1
        )

    def open(self):
        self.ser.open()

    def isOpen(self):
        return self.ser.isOpen()

    def send(self, commands):
        self.ser.write((self.RECORD_SEPARATOR.join(
            commands) + self.RECORD_SEPARATOR).encode())

    def listen(self):
        # events = []
        n = self.ser.inWaiting()
        if n > 0:
            try:
                self.readbuffer = self.ser.read(n) 
            except Exception as e:
                print("Exception " + e + " while reading from Serial port")

        return self.readbuffer
