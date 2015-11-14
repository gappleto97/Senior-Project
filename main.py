from common.bounty import *
from common.peers import *
from common import settings
from time import sleep
from common.safeprint import safeprint
import pickle

def main():
    settings.setup()
    try:
        import miniupnpc
    except:
        settings.config['outbound'] = True
    safeprint("settings are:")
    safeprint(settings.config)
    ear = listener(settings.config['port'],settings.config['outbound'])
    ear.daemon = True
    ear.start()
    sleep(5)
    initializePeerConnections(settings.config['port'])
    #######TEST SECTION#######
    safeprint("Correctly formed bounty")
    test = Bounty('8.8.8.8:8888',"1JTGcHS3GMhBGLcFRuHLk6Gww4ZEDmP7u9",1090)
    safeprint(test)
    safeprint(test.isValid())
    a = pickle.dumps(test,1)
    if type(a) != type("a".encode('utf-8')):
        a = a.encode('utf-8')
    safeprint(verify(a))
    safeprint("Malformed bounty 1 (ip failure)")
    test = Bounty('8.8.8.8',"1JTGcHS3GMhBGLcFRuHLk6Gww4ZEDmP7u9",1090)
    safeprint(test)
    safeprint(test.isValid())
    a = pickle.dumps(test,1)
    if type(a) != type("a".encode('utf-8')):
        a = a.encode('utf-8')
    safeprint(verify(a))
    safeprint("Malformed bounty 2 (ip failure)")
    test = Bounty('8.8.8:8888',"1JTGcHS3GMhBGLcFRuHLk6Gww4ZEDmP7u9",1090)
    safeprint(test)
    safeprint(test.isValid())
    a = pickle.dumps(test,1)
    if type(a) != type("a".encode('utf-8')):
        a = a.encode('utf-8')
    safeprint(verify(a))
    safeprint("Malformed bounty 3 (btc failure)")
    test = Bounty('8.8.8.8:8888',"1JTGcHS3GMhBGGww4ZEDmP7u9",1090)
    safeprint(test)
    safeprint(test.isValid())
    a = pickle.dumps(test,1)
    if type(a) != type("a".encode('utf-8')):
        a = a.encode('utf-8')
    safeprint(verify(a))
    safeprint("Malformed bounty 4 (reward failure)")
    test = Bounty('8.8.8.8:8888',"1JTGcHS3GMhBGLcFRuHLk6Gww4ZEDmP7u9",-1090)
    safeprint(test)
    safeprint(test.isValid())
    a = pickle.dumps(test,1)
    if type(a) != type("a".encode('utf-8')):
        a = a.encode('utf-8')
    safeprint(verify(a))
    
if __name__ == "__main__":
    main()
