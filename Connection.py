# Connection
#
#   Base class for various sources of stream data
#


class Connection:
    def __init__(self):
        self.readbuffer = ''
        # self.open()

    def open(self):
        print('YOU MUST OVERRIDE THIS METHOD')
    
    def isOpen(self):
        print('YOU MUST OVERRIDE THIS METHOD')

    def listen(self):
        print('YOU MUST OVERRIDE THIS METHOD')
