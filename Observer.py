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


    