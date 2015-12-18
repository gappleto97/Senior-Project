from common import bounty
from common.peers import *
from common import settings
from common.safeprint import safeprint
from multiprocessing import Queue, Value
from time import sleep, time
import pickle

def sync():
    from multiprocessing import Manager
    from common import bounty, settings, peers
    man = Manager()
    items = {'config':man.dict(),
             'peerList':man.list(),
             'bountyList':man.list(),
             'bountyLock':bounty.bountyLock,
             'keyList':man.list(),
             'myPub':(peers.myPriv.n,peers.myPriv.e),
             'myPriv':(peers.myPriv.n,peers.myPriv.e,peers.myPriv.d,peers.myPriv.p,peers.myPriv.q)}
    items['config'].update(settings.config)
    items['peerList'].extend(peers.peerlist)
    items['bountyList'].extend(bounty.bountyList)
    items['keyList'].extend(bounty.keyList)
    safeprint(items)
    safeprint(items.get('bountyList'))
    safeprint(items.get('keyList'))
    if items.get('config') is not None:
        from common import settings
        settings.config = items.get('config')
    if items.get('peerList') is not None:
        global peerList
        peers.peerlist = items.get('peerList')
    if items.get('bountyList') is not None:
        from common import bounty
        bounty.bountyList = items.get('bountyList')
    if items.get('bountyLock') is not None:
        from common import bounty
        bounty.bountyLock = items.get('bountyLock')
    if items.get('keyList') is not None:
        from common import bounty
        bounty.keyList = items.get('keyList')
    if items.get('myPub') is not None:
        from common import peers
        from rsa import PublicKey
        peers.myPub = PublicKey(*items.get('myPub'))
    if items.get('myPriv') is not None:
        from common import peers
        from rsa import PrivateKey
        peers.myPriv = PrivateKey(*items.get('myPriv'))
    return items

def main():
    settings.setup()
    try:
        import miniupnpc
    except:
        safeprint("Dependency miniupnpc is not installed. Running in outbound only mode")
        settings.config['outbound'] = True
    safeprint("settings are:")
    safeprint(settings.config)
    queue = Queue()
    live = Value('b',True)
    ear = listener(settings.config['port'],settings.config['outbound'],queue,live,settings.config['server'])
    ear.daemon = True
    ear.items = sync()
    ear.start()
    mouth = propagator(settings.config['port'] + 1, live)
    mouth.daemon = True
    mouth.items = ear.items
    mouth.start()
    feedback = []
    stamp = time()
    while queue.empty():
        if time() - 5 > stamp:
            break #pragma: no cover
    try:
        feedback = queue.get(False)
    except: #pragma: no cover
        safeprint("No feedback received from listener")
    ext_ip = ""     #Does this affect peers?
    ext_port = -1   #Does this affect peers?
    if feedback != []:
        settings.outbound = feedback[0]
        if settings.outbound is not True:
            ext_ip = feedback[1]
            ext_port = feedback[2]
    initializePeerConnections(settings.config['port'], ext_ip, ext_port)
    live.value = False

if __name__ == "__main__":
    main()
