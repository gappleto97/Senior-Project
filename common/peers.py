from multiprocessing import Queue
import multiprocessing, os, pickle, select, socket, sys, time, rsa
from common.safeprint import safeprint
from common.bounty import *

global ext_port
global ext_ip
global port
global myPriv
global myPub
ext_port = -1
ext_ip = ""
port = 44565
myPub, myPriv = rsa.newkeys(1024)

seedlist = [(("127.0.0.1",44565),myPub.n,myPub.e), (("localhost",44565),myPub.n,myPub.e), (("10.132.80.128",44565),myPub.n,myPub.e)]
peerlist = [(("24.10.111.111",44565),)]
remove   = []
bounties = []

#constants
peers_file      = "data" + os.sep + "peerlist.pickle"
key_request     = "Key Request".encode('utf-8')
close_signal    = "Close Signal".encode("utf-8")
peer_request    = "Requesting Peers".encode("utf-8")
bounty_request  = "Requesting Bounties".encode("utf-8")
incoming_bounty = "Incoming Bounty".encode("utf-8")
valid_signal    = "Bounty was valid".encode("utf-8")
invalid_signal  = "Bounty was invalid".encode("utf-8")
end_of_message  = "End of message".encode("utf-8")

sig_length = len(max(close_signal,peer_request,bounty_request,incoming_bounty,valid_signal,invalid_signal,key=len))

def pad(string):
    return string + " ".encode('utf-8') * (sig_length - (((len(string) - 1) % sig_length) + 1))

close_signal    = pad(close_signal)
peer_request    = pad(peer_request)
bounty_request  = pad(bounty_request)
incoming_bounty = pad(incoming_bounty)
valid_signal    = pad(valid_signal)
invalid_signal  = pad(invalid_signal)
end_of_message  = pad(end_of_message)

def findKey(addr):
    for i in peerlist[:]:
        if addr == i[0]:
            return rsa.PublicKey(i[1],i[2])
    return None

def send(msg, conn, key):
    if key is None:
        conn.send(key_request)
        a = conn.recv(1024)
        safeprint("Receive: " + str(a))
        key = pickle.loads(a)
        safeprint(key)
        key = rsa.PublicKey(key[0],key[1])
    safeprint(key)
    if len(msg) <= 117:
        conn.sendall(rsa.encrypt(msg,key))
    else:
        x = 0
        while x < len(msg) - 117:
            conn.sendall(rsa.encrypt(msg[x:x+117],key))
            x += 117
        conn.sendall(rsa.encrypt(msg[x:],key))
    conn.sendall(rsa.encrypt(end_of_message,key))

def recv(conn):
    safeprint(myPriv)
    connected = True
    received = ""
    while connected:
        a = conn.recv(128)
        if a == key_request:
            safeprint("I had my key requested on receive")
            a = pickle.dumps((myPriv.n,myPriv.e))
            safeprint("Sending: " + str(a))
            conn.sendall(a)
            continue
        a = rsa.decrypt(a,myPriv)
        if a != end_of_message:
            received += a
        else:
            connected = False
        if received in [close_signal,peer_request,bounty_request,incoming_bounty,valid_signal,invalid_signal]:
            return received
    return received

if os.name != "nt":
    import fcntl
    import struct

    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                                ifname[:15]))[20:24])

def get_lan_ip():
    """Retrieves the LAN ip. Unfortunately uses an external connection in Python 3."""
    if sys.version_info[0] < 3:
        ip = socket.gethostbyname(socket.gethostname())
        if ip.startswith("127.") and os.name != "nt":
            interfaces = ["eth0","eth1","eth2","wlan0","wlan1","wifi0","ath0","ath1","ppp0",]
            for ifname in interfaces:
                try:
                    ip = get_interface_ip(ifname)
                    break
                except IOError:
                    pass
        return ip
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 0))
        a = s.getsockname()[0]
        s.close()
        return a

def getFromFile():
    """Load peerlist from a file"""
    if os.path.exists(peers_file):
        try:
            peerlist = pickle.load(open(peers_file,"rb"))
        except:
            safeprint("Could not load peerlist from file")

def saveToFile():
    """Save peerlist to a file"""
    if not os.path.exists(peers_file.split(os.sep)[0]):
        os.mkdir(peers_file.split(os.sep)[0])
    pickle.dump(peerlist,open(peers_file,"wb"),0)

def getFromSeeds():
    """Make peer requests to each address on the seedlist"""
    for seed in seedlist:
        safeprint(seed)
        peerlist.extend(requestPeerlist(seed))
        time.sleep(1)

def requestPeerlist(address):
    """Request the peerlist of another node. Currently has additional test commands"""
    conn = socket.socket()
    conn.settimeout(5)
    safeprint(address)
    try:
        conn.connect(address[0])
        key = findKey(address[0])
        send(peer_request,conn,key)
        received = recv(conn)
        safeprint(pickle.loads(received))
        #test section
        conn = socket.socket()
        conn.settimeout(5)
        conn.connect(address[0])
        send(incoming_bounty,conn,key)
        bounty = Bounty(get_lan_ip() + ":44565","1JTGcHS3GMhBGLcFRuHLk6Gww4ZEDmP7u9",1440)
        bounty = pickle.dumps(bounty,0)
        if type(bounty) == type("a"):
            bounty = bounty.encode('utf-8')
        safeprint(bounty)
        send(bounty,conn,key)
        send(close_signal,conn,key)
        conn.close()
        #end test section
        return pickle.loads(received)
    except Exception as error:
        safeprint("Failed:" + str(type(error)))
        safeprint(error)
        remove.extend([address])
        return []

def requestBounties(address):
    """Request the bountylist of another node"""
    conn = socket.socket()
    conn.settimeout(5)
    safeprint(address)
    try:
        conn.connect(address[0])
        key = findKey(address[0])
        send(bounty_request,conn,key)
        received = recv(conn)
        send(close_signal,conn,key)
        conn.close()
        try:
            safeprint(pickle.loads(received))
            bounties = pickle.loads(received)
            for bounty in bounties:
                addBounty(pickle.dumps(bounty,0))
                safeprint("Bounty added")
        except Exception as error:
            safeprint("Could not add bounties. This is likely because you do not have the optional dependency PyCrypto")
            safeprint(type(error))
            #later add function to request without charity bounties
    except Exception as error:
        safeprint("Failed:" + str(type(error)))
        safeprint(error)
        remove.extend([address])

def initializePeerConnections(newPort,newip,newport):
    """Populate the peer list from a previous session, seeds, and from the peer list if its size is less than 12. Then save this new list to a file"""
    port = newPort        #Does this affect the global variable?
    ext_ip = newip        #Does this affect the global variable?
    ext_port = newport    #Does this affect the global variable?
    safeprint([ext_ip, ext_port])
    getFromFile()
    safeprint("peers fetched from file")
    getFromSeeds()
    safeprint("peers fetched from seedlist")
    trimPeers()
    if len(peerlist) < 12:
        safeprint(len(peerlist))
        newlist = []
        for peer in peerlist:
            newlist.extend(requestPeerlist(peer))
        peerlist.extend(newlist)
    trimPeers()
    safeprint("peer network extended")
    saveToFile()
    safeprint("peer network saved to file")
    safeprint(peerlist)
    safeprint([ext_ip, ext_port])

def trimPeers():
    """Trim the peerlist to a single set, and remove any that were marked as erroneous before"""
    temp = list(set(peerlist[:]))
    for peer in remove:
        try:
            del temp[temp.index(peer)]
        except:
            continue
    del remove[:]
    del peerlist[:]
    peerlist.extend(temp)

def listen(port, outbound, q, v, serv):
    """BLOCKING function which should only be run in a daemon thread. Listens and responds to other nodes"""
    if serv:
        from server.bounty import verify, addBounty
    server = socket.socket()
    server.bind(("0.0.0.0",port))
    server.listen(10)
    server.settimeout(5)
    if sys.version_info[0] < 3 and sys.platform == "win32":
        server.setblocking(True)
    ext_ip = ""
    ext_port = -1
    if outbound is True:
        safeprint("UPnP mode is disabled")
    else:
        safeprint("UPnP mode is enabled")
        if not portForward(port):
            outbound = True
    safeprint([outbound,ext_ip, ext_port])
    q.put([outbound,ext_ip,ext_port])
    while v.value:    #is True is implicit
        safeprint("listening on " + str(get_lan_ip()) + ":" + str(port))
        if not outbound:
            safeprint("forwarded from " + ext_ip + ":" + str(ext_port))
        try:
            conn, addr = server.accept()
            server.setblocking(True)
            conn.setblocking(True)
            safeprint("connection accepted")
            packet = recv(conn)
            safeprint("Received: " + packet.decode())
            if packet == peer_request:
                handlePeerRequest(conn,True)
            elif packet == bounty_request:
                handleBountyRequest(conn)
            elif packet == incoming_bounty:
                handleIncomingBounty(conn)
            send(close_signal,conn,key)
            conn.close()
            server.settimeout(5)
            safeprint("connection closed")
        except Exception as error:
            safeprint("Failed: " + str(type(error)))
            safeprint(error)

def handlePeerRequest(conn, exchange):
    """Given a socket, send the proper messages to complete a peer request"""
    if ext_port != -1:
        toSend = pickle.dumps(peerlist[:] + [((ext_ip,ext_port),myPub.n,myPub.e)],0)
    toSend = pickle.dumps(peerlist[:],0)
    if type(toSend) != type("a".encode("utf-8")):
        safeprint("Test here")
        toSend = toSend.encode("utf-8")
    key = findKey(conn.getsockname())
    safeprint("Sending")
    send(toSend,conn,key)
    if exchange:
        send(peer_request,conn,key)
        received = recv(conn)
        peerlist.extend(pickle.loads(received))
        trimPeers()

def handleIncomingBounty(conn):
    """Given a socket, store an incoming bounty, and report it valid or invalid"""
    key = findKey(conn.getsockname())
    received = recv(conn)
    safeprint("Adding bounty: " + received.decode())
    try:
        if addBounty(received):
            send(valid_signal,conn,key)
            mouth = socket.socket()
            import settings
            mouth.connect(("localhost",settings.config['port'] + 1))
            mouth.send(incoming_bounty)
            mouth.send(pad(received))
            mouth.send(close_signal)
            mouth.close()
        else:
            send(invalid_signal,conn,key)
    except:
        safeprint("They closed too early")

def handleIncomingBountyP(conn):
    """Given a socket, store an incoming bounty, and report it valid or invalid"""
    connected = True
    received = "".encode('utf-8')
    while connected:
        packet = conn.recv(sig_length)
        safeprint(packet)
        if not packet == close_signal:
            received += packet
        else:
            connected = False
    safeprint("Adding bounty: " + received.decode())
    try:
        bounty = pickle.loads(received)
        if bounty.isValid():
            from multiprocessing.pool import ThreadPool
            ThreadPool().map(propagate,[(bounty,x) for x in peerlist[:]])
    except Exception as error:
        safeprint("bounty propagation failed: " + str(type(error)))
        safeprint(error)
        return False

def propagate(tup):
    try:
        conn = socket.socket()
        address = tup[1]
        conn.connect(address[0])
        key = findKey(conn.getsockname())
        if key is None:
            conn.send(key_request)
            key = pickle.loads(conn.recv(1024))
            safeprint(key)
            key = rsa.PublicKey(key[0],key[1])
        send(incoming_bounty,conn,key)
        send(pad(pickle.dumps(tup[0],0)),conn,key)
        recv(conn)
        conn.close()
    except socket.error as Error:
        safeprint("Connection to " + str(address) + " failed; cannot propagate")

def portForward(port):
    """Attempt to forward a port on your router to the specified local port. Prints lots of debug info."""
    try:
        import miniupnpc
        u = miniupnpc.UPnP(None, None, 200, port)
        #Begin Debug info
        safeprint('inital(default) values :')
        safeprint(' discoverdelay' + str(u.discoverdelay))
        safeprint(' lanaddr' + str(u.lanaddr))
        safeprint(' multicastif' + str(u.multicastif))
        safeprint(' minissdpdsocket' + str(u.minissdpdsocket))
        safeprint('Discovering... delay=%ums' % u.discoverdelay)
        safeprint(str(u.discover()) + 'device(s) detected')
        #End Debug info
        u.selectigd()
        global ext_ip
        ext_ip = u.externalipaddress()
        safeprint("external ip is: " + str(ext_ip))
        for i in range(0,20):
            try:
                safeprint("Port forward try: " + str(i))
                if u.addportmapping(port+i, 'TCP', get_lan_ip(), port, 'Bounty Net', ''):
                    global ext_port
                    ext_port = port + i
                    safeprint("External port is " + str(ext_port))
                    return True
            except Exception as error:
                safeprint("Failed: " + str(type(error)))
                safeprint(error)
    except Exception as error:
        safeprint("Failed: " + str(type(error)))
        safeprint(error)
        return False

def listenp(port, v):
    """BLOCKING function which should only be run in a daemon thread. Listens and responds to other nodes"""
    server = socket.socket()
    server.bind(("0.0.0.0",port))
    server.listen(10)
    server.settimeout(5)
    if sys.version_info[0] < 3 and sys.platform == "win32":
        server.setblocking(True)
    while v.value:    #is True is implicit
        safeprint("listenp-ing on localhost:" + str(port))
        try:
            conn, addr = server.accept()
            server.setblocking(True)
            conn.setblocking(True)
            safeprint("connection accepted")
            packet = conn.recv(sig_length)
            safeprint("Received: " + packet.decode())
            if packet == incoming_bounty:
               handleIncomingBountyP(conn)
            conn.send(close_signal)
            conn.close()
            server.settimeout(5)
            safeprint("connection closed")
        except Exception as error:
            safeprint("Failed: " + str(type(error)))
            safeprint(error)

class listener(multiprocessing.Process): #pragma: no cover
    """A class to deal with the listener method"""
    def __init__(self, port, outbound, q, v, serv):
        multiprocessing.Process.__init__(self)
        self.outbound = outbound
        self.port = port
        self.q = q
        self.v = v
        self.serv = serv
    def run(self):
        safeprint("listener started")
        self.sync(self.items)
        listen(self.port,self.outbound,self.q,self.v,self.serv)
        safeprint("listener stopped")
    def sync(self,items):
        if items == {}:
            return
        if items.get('config'):
            from common import settings
            settings.config = items.get('config')
        if items.get('peerList'):
            global peerlist
            peerList = items.get('peerList')
        if items.get('bountyList'):
            from common import bounty
            bounty.bountyList = items.get('bountyList')
        if items.get('bountyLock'):
            from common import bounty
            bounty.bountyLock = items.get('bountyLock')
        if items.get('keyList'):
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

class propagator(multiprocessing.Process): #pragma: no cover
    """A class to deal with the listener method"""
    def __init__(self, port, v):
        multiprocessing.Process.__init__(self)
        self.port = port
        self.v = v
    def run(self):
        safeprint("propagator started")
        self.sync(self.items)
        listenp(self.port, self.v)
        safeprint("propagator stopped")
    def sync(self,items):
        if items == {}:
            return
        if items.get('config'):
            from common import settings
            settings.config = items.get('config')
        if items.get('peerList'):
            global peerlist
            peerList = items.get('peerList')
        if items.get('bountyList'):
            from common import bounty
            bounty.bountyList = items.get('bountyList')
        if items.get('bountyLock'):
            from common import bounty
            bounty.bountyLock = items.get('bountyLock')
        if items.get('keyList'):
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
