import os, pickle, re, sys
from common.safeprint import safeprint
from multiprocessing import Lock
from hashlib import sha256

global bountyList
global bountyLock
global bountyPath
global keyList
bountyList = []
bountyLock = Lock()
bounty_path = "data" + os.sep + "bounties.pickle"
keyList = []

def getUTC():
    from calendar import timegm
    from time import gmtime
    return timegm(gmtime())

class Bounty(object):
    """An object representation of a Bounty
    Parts:
    ip         -- The ip address of the requesting node
    btc        -- The Bitcoin address of the requesting party
    reward     -- The reward amount in satoshis to be given over 24 hours
                   (x | x == 0 or 1440 <= x <= 100000000) (1440 is 1 satoshi/minute)
    ident      -- A value set by the issuer to determine which problem/test to send
    timeout    -- Unix time at which the bounty expires (defaults to 24 hours)
    data       -- A dictionary containing optional, additional information
        author -- String which represents the group providing the Bounty
        reqs   -- Dict containing requirements keyed by the related python calls
                   ("sys.platform":"win32")
        perms  -- Dict containing the minimum required security policies
                   (if empty, most restrictive assumed)
        key    -- An RSA object (via Pycrypto) which contains the public key for this Bounty
                   (required only when reward is 0)
        sig    -- A tuple of the Bounty's print output signed by the above key
                   (required only when reward is 0)
        TDL    -- More to be defined in later versions
    """

    def __repr__(self):
        """Gives a string representation of the bounty"""
        output = "<Bounty: ip=" + str(self.ip) + ", btc=" + str(self.btc) + ", reward=" + str(self.reward)
        if self.ident != None:
            output = output + ", id=" + str(self.ident)
        if self.timeout != None:
            output = output + ", timeout=" + str(self.timeout)
        if self.data and self.data != {'author':'','reqs':{},'perms':{}}:
            if self.data.get('author') and self.data.get('author') != '':
                output = output + ", author=" + str(self.data.get('author'))
            if self.data.get('reqs') and self.data.get('reqs') != {}:
                output = output + ", reqs=" + str(self.data.get('reqs'))
            if self.data.get('perms') and self.data.get('perms') != {}:
                output = output + ", perms=" + str(self.data.get('perms'))
        return output + ">"

    def __eq__(self, other):
        """Determines whether the bounties are equal"""
        return (self.reward == other.reward) and (self.ident == other.ident) and (self.data == other.data)
        
    def __ne__(self, other):
        """Determines whether the bounties are unequal"""
        return not self.__eq__(other)
        
    def __lt__(self, other):
        """Determines whether this bounty has a lower priority"""
        if self.reward < other.reward:
            return True
        elif self.timeout < other.timeout:
            return True
        else:
            return False
        
    def __gt__(self, other):
        """Determines whether this bounty has a higher priority"""
        if self.reward > other.reward:
            return True
        elif self.timeout > other.timeout:
            return True
        else:
            return False
        
    def __le__(self, other):
        """Determines whether this bounty has a lower priority or is equal"""
        boolean = self.__lt__(other)
        if boolean:
            return boolean
        else:
            return self.__eq__(other)
        
    def __ge__(self, other):
        """Determines whether this bounty has a higher or is equal"""
        boolean = self.__gt__(other)
        if boolean:
            return boolean
        else:
            return self.__eq__(other)
      
    def __init__(self, ipAddress, btcAddress, rewardAmount, timeout=None, ident=None, dataDict={}, keypair=None):
        """Initialize a Bounty; constructor"""
        self.ip = ipAddress
        self.btc = btcAddress
        self.reward = rewardAmount
        self.ident = None
        if timeout is not None:
            self.timeout = timeout
        else:
            self.timeout = getUTC() + 86400
        self.data = {'author':'',
                     'reqs':{},
                     'perms':{}}
        if ident is not None:
            self.ident = None
        if dataDict is not None:
            self.data.update(dataDict)
        if keypair is not None:
            self.sign(keypair)

    def isValid(self):
        """Internal method which checks the Bounty as valid under the most minimal version

        ip      -- Must be in valid range
        btc     -- Must be in valid namespace
        reward  -- Must be in valid range
        timeout -- Must be greater than the current time
        """
        try:
            safeprint("Testing IP address")
            boolean = int(self.ip.split(":")[1]) in range(1024,49152)
            for sect in self.ip.split(":")[0].split("."):
                boolean = int(sect) in range(0,256) and boolean
            if not boolean:
                return False
            safeprint("Testing Bitcoin address")
            address = str(self.btc)
            #The following is a soft check
            #A deeper check will need to be done in order to assure this is correct
            if not checkAddressValid(address):
                return False
            safeprint("Testing reward")
            reward = int(self.reward)
            boolean = reward >= 1440 and reward <= 100000000
            if reward == 0 or reward is None:
                safeprint("Testing signature validity")
                boolean = self.checkSign()
            if boolean is False:
                return False
            safeprint("Testing timeout")
            if self.timeout < getUTC(): #check against current UTC
                return False
            from common.call import parse
            safeprint("Testing bounty requirements")
            return parse(self.data.get('reqs'))
        except:
            return False

    def isPayable(self, factor):
        """check if address has enough"""
        return True #later make this a wrapper for pywallet.balance()

    def checkSign(self):
        safeprint(keyList)
        if self.data.get('key') in keyList:
            expected = str(self).encode('utf-8')
            if not self.data['key'].size() / 4 + 1 < len(expected):
                return self.data['key'].verify(expected,self.data['sig'])
        return False

    def sign(self,keypair):
        expected = str(self).encode('utf-8')
        if keypair.size() / 4 + 1 < len(expected):
            return False
        self.data.update({"sig":keypair.sign(expected,64),"key":keypair.publickey()})
        return True

def addKey(key):
    global keyList
    keyList.append(key)

def checkAddressValid(address):
    """Check to see if a Bitcoin address is within the valid namespace. Will potentially give false positives based on leading 1s"""
    if not re.match(re.compile("^[a-km-zA-HJ-Z1-9]{26,35}$"),address):
        return False
    decimal = 0
    for char in address:
        decimal = decimal * 58 + '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'.index(char)
    if sys.version_info[0] < 3:
        """long does not have a to_bytes() in versions less than 3. This is an equivalent function"""
        bcbytes = (('%%0%dx' % (25 << 1) % decimal).decode('hex')[-25:])
        return bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]
    else:
        bcbytes = decimal.to_bytes(25, 'big')
        return bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]

def verify(string):
    """External method which checks the Bounty as valid under implementation-specific requirements. This can be defined per user.

    ip      -- Must be in valid range
    btc     -- Must be in valid namespace
    reward  -- Must be in valid range
    timeout -- Must be greater than the current time
    """
    test = None
    if type(string) == type(Bounty(None,None,None)):
        test = string
    else:
        try:
            test = pickle.loads(string)
        except:
            return False
    try:
        safeprint("Testing IP address")
        boolean = int(test.ip.split(":")[1]) in range(1024,49152)
        for sect in test.ip.split(":")[0].split("."):
            boolean = int(sect) in range(0,256) and boolean
        if not boolean:
            return False
        safeprint("Testing Bitcoin address")
        address = str(test.btc)
        #The following is a soft check
        #A deeper check will need to be done in order to assure this is correct
        if not checkAddressValid(address):
            return False
        safeprint("Testing reward")
        reward = int(test.reward)
        boolean = reward >= 1440 and reward <= 100000000
        if reward == 0 or reward is None:
            safeprint("Testing signature validity")
            boolean = test.checkSign()
        if boolean is False:
            return False
        safeprint("Testing timeout")
        if test.timeout < getUTC(): #check against current UTC
            return False
        from common.call import parse
        safeprint("Testing bounty requirements")
        return parse(test.data.get('reqs'))
    except:
        return False

def getBountyList():
    """Retrieves the bounty list. Temporary method"""
    temp = []
    with bountyLock:
        temp = bountyList
    return temp

def saveToFile(bountyList):
    """Save the current bounty list to a file"""
    if not os.path.exists(bounty_path.split(os.sep)[0]):
        os.mkdir(bounty_path.split(os.sep)[0])
    pickle.dump(bountyList,open(bounty_path, "wb"),0)
    return True

def loadFromFile():
    """Load a previous bounty list from a file"""
    if os.path.exists(bounty_path):
        with bountyLock:
            bountyList = pickle.load(open(bounty_path,"rb"))
        return True
    return False

def addBounty(bounty):
    """Verify a bounty, and add it to the list if it is valid"""
    first = False
    safeprint([sys.version_info[0],sys.version_info[1],sys.version_info[2]])
    if sys.version_info[0] == 2 and sys.version_info[1] == 6 and (type(bounty) == type("aaa") or type(bounty) == type(unicode("aaa"))):
        safeprint("Fed as string in 2.6; encoding ascii and ignoring errors")
        try:
            bounty = bounty.encode('ascii','ignore')
        except:
            bounty = str(bounty)
    elif type(bounty) == type("aaa") and sys.version_info[0] >= 3:
        safeprint("Fed as string; encoding utf-8")
        bounty = bounty.encode('utf-8')
    safeprint(pickle.loads(bounty))
    safeprint("External verify")
    try:
        bounty = pickle.loads(bounty)
    except:
        return False
    first = verify(bounty)
    safeprint("Internal verify")
    second = bounty.isValid()
    if first and second:
        with bountyLock:
            bountyList.append(bounty)
    return (first and second)

def getBounty(charity, factor):
    """Retrieve the next best bounty from the list"""
    temp = getBountyList()
    safeprint("bountyList = " + str(temp))
    if temp == []:
        return None
    elif charity:
        for bounty in temp:
            if bounty.isValid():
                index = temp.index(bounty)
                return temp.pop(index)
    else:
        best = None
        for bounty in temp:
            if best is None:
                best = bounty
            elif best < bounty and bounty.isValid() and bounty.isPayable(factor):
                best = bounty
        return best
