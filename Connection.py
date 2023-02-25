# Connection
#
#   Base class for various sources of stream data
#


class Connection:
    def __init__(self):
        self.readbuffer = ''
        # self.open()

    def open(self):
        pass
    
    def isOpen(self):
        pass

    def listen(self):
        pass

class IOConnection(Connection):
    def send(self, message):
        pass
