# FileReader
#   Really just a mock for some basic testing without the Serial port or a way to replay key bits
#
#   no size limiting, no chunking, very simple
#

from Connection import Connection


class FileReader(Connection):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.file = None

        # self.open()

    def __del__(self):  
        self.close()      

    def isOpen(self):
        return (self.file is not None)

    def open(self):
        try:
            self.file = open(self.filename, 'rb')
        except Exception as err:
            print(f'error opening {self.filename}: {err}')

    def close(self):   
        if self.file is not None:
            self.file.close()
            self.file = None

    def listen(self):
        try:
            self.readbuffer = self.file.read() 
        except Exception as e:
            print("Exception " + e + " while reading from file")

        return self.readbuffer


  