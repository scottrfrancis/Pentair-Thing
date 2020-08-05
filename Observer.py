# Basic (simplistic?) implementation of Observer pattern
#

''' To Use:
- subclass Observable for a thing that chagnes
- subclass Observer for the things that will use those changes

- Observers call Observable's #addObserver to register and #removeObserver to stop

- When the thing (the Observable) changes, #notifyObservers calls all the Observers
'''




class Observer:
    def update(observable, arg):
        '''Called when observed object is modified, from list
        of Observers in object via notifyObservers.
        Observers must first register with Observable.'''
        pass

'''NOTE: NOT Implementing the thread synchronization from
https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Observer.html
for simplicity'''

class Observable:
    def __init__(self):
        self.observers = []
        self.changed = False
    
    def addObserver(self, observer):
        if observer not in self.observers:
            self.observers.append(observer)

    def removeObserver(self, observer):
        self.observers.remove(observer)

    def notifyObservers(self, arg = None):
        try:
            observers = self.observers
            self.changed = False

            for o in observers:
                o.update(arg)
        except Exception as err:
            pass


def mkObs(cls):
    class Wrapper(cls):
        def __init__(self, x=None):
            print(f"init wrapper with {x}")
            super().__init__(x)
            # self.wrap = cls(x)
            # print(f'wrap is {self.wrap}')
            self.dirty = False

        def __setitem__(self, key, item):
            print(f'set item: {key}:{item}')
            # self.wrap.__setitem__(key, item)
            super().__setitem__(key, item)
            self.dirty = True
            print(f'{self.dirty}')
            
    return Wrapper



# an observable chunk of raw data from the serial port, or a file, or ?
class ObservableString(Observable):
    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.chunk = b''

    # call to add to the end of the chunk, notifies observers
    def append(self, increment):
        if len(increment) > 0:
            self.chunk = self.chunk + increment

            self.notifyObservers(self.chunk)
            self.clear()

# an Observaable wrapped array
class ObservableArray(Observable):
    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.elements = []

    def append(self, newElements):
        if len(newElements) > 0:
            self.elements.extend(newElements)

            self.notifyObservers(self.elements)
            self.clear()

# an Observable wrapped dict
class ObservableDict(Observable):
    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.dict = {}

    def append(self, newDict):
        if len(newDict) > 0:
            self.dict.update(newDict)

            self.notifyObservers(self.dict)
            

    def getDict(self):
        return self.dict

    