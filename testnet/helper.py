from dataclasses import dataclass
import json
import random
import sys
from coincurve import PrivateKey, PublicKey
import hashlib
from ecies import decrypt
from ecies.utils import decapsulate, hex2prv, aes_decrypt
import matplotlib.pyplot as plt
from operator import attrgetter

### Order Dataclass ###
@dataclass
class Order:
    client: bytes = ''
    type: str = ''
    asset: str = ''
    price: int = 0
    volume: int = 0
    mes: int = 0
    secret: bytes = ''

    def copy(self):
        return Order(self.client, self.type, self.asset, self.price,
                     self.volume, self.mes, self.secret)

# compile smart contract first (with truffle)
def deploy_contract(w3, contract_path):
    # open compiled file
    truffleFile = json.load(open(contract_path))
    # get abi and bytecode
    abi = truffleFile['abi']
    bytecode = truffleFile['bytecode']
    # instanciate contract
    DarkPool = w3.eth.contract(abi=abi, bytecode=bytecode)
    # deploy contract (call constructor)
    tx_hash = DarkPool.constructor().transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print("Contract deployed at address: {} and block: {}"
          .format(tx_receipt.contractAddress, w3.eth.blockNumber))
    print("Gas used:", tx_receipt.gasUsed)
    return tx_receipt.contractAddress

# produce a random order
def create_random_order(assets, p_lim=100, v_lim=100):
    type = random.choice(['b', 's'])
    asset = random.choice(assets)
    price = random.choice(range(1,p_lim))
    vol = random.choice(range(1,v_lim))
    mes = random.choice(range(vol+1))
    return Order('', type, asset, price, vol, mes, '')

def shared_secret(sk, ciphertext):
    if isinstance(sk, str):
        private_key = hex2prv(sk)
    elif isinstance(sk, bytes):
        private_key = PrivateKey(sk)
    else:
        raise TypeError("Invalid secret key type")

    pubkey = ciphertext[0:65]
    ephemeral_public_key = PublicKey(pubkey)

    aes_key = decapsulate(ephemeral_public_key, private_key)
    return aes_key

def decrypt_shared_secret(aes_key, ciphertext):
    encrypted = ciphertext[65:]
    return aes_decrypt(aes_key, encrypted)

def validate_commitment(assets, address, commitment, ciphertext, secret, type):
    if commitment == hashlib.sha3_256(ciphertext).digest():
        try:
            # based on which key I know, decrypt ciphertext to get order
            if type: # if private key is known -> operator
                order_bytes = decrypt(secret, ciphertext)
            else: # if shared secret is known -> everyone else
                order_bytes = decrypt_shared_secret(secret, ciphertext)
        except Exception as e:
            # status 1: commitment doesn't match ciphertext
            error = "Decryption error: " + str(e)
            return -1, error

        # DANGER WORKING WITH USER INPUT!!! NEED TO MAKE SAFE
        try:
            # strip nonce away
            order_bytes = order_bytes[:-32]
            # decode bytes into string
            order_string = order_bytes.decode()

            # check if the order is empty
            if order_string == "None":
                # status 1: order is empty, return it
                return 1, order_string
            else:
                # split order into its parts
                order_list = order_string.split(",")
                order = Order()
                # add client to order
                order.client = address
                # check type
                if order_list[0] == 's' or order_list[0] == 'b':
                    order.type = order_list[0]
                else:
                    raise Exception()
                # check asset
                if order_list[1] in assets:
                    order.asset = order_list[1]
                else:
                    raise Exception()
                # turn price into integer
                order_list[2] = int(order_list[2])
                # price must be non-negative
                if order_list[2] < 0:
                    raise Exception()
                else:
                    order.price = order_list[2]
                # turn volume into integer
                order_list[3] = int(order_list[3])
                # volume must be at least 1
                if order_list[3] < 1:
                    raise Exception()
                else:
                    order.volume = order_list[3]
                # turn mes into int
                order_list[4] = int(order_list[4])
                # mes must be an integer in [0,vol]
                if order_list[4] > order.volume or order_list[4] < 0:
                    raise Exception()
                else:
                    order.mes = order_list[4]
                # all checks passed => mark order as valid
                # status 0: order is valid, return it
                return 0, order
        except:
            # status 2: order not according to specification
            return -1, "Order not according to specification, therefore invalid."
    else:
        # status 1: commitment doesn't match ciphertext
        return -1, "Commitment doesn't match ciphertext, order invalid."

def match(matching, asset, bids, asks, verbose, graph_verbose):
    clearedPrice = -1
    clearedOrders = []
    if matching == 0:
        # sort bids and asks
        # bids are sorted by price (des) and then volume (des)
        bids.sort(key=attrgetter("volume"), reverse=True)
        bids.sort(key=attrgetter("price"), reverse=True)
        # asks are sorted by price (asc) and then volume (des)
        asks.sort(key=attrgetter("volume"), reverse=True)
        asks.sort(key=attrgetter("price"))

        # get supply and demand curves
        if graph_verbose:
            plt = supply_demand_plot(bids, asks)
        # perform periodic auction matching
        clearedOrders, clearedPrice = periodic_auction(bids, asks)
        if verbose:
            # print results
            for c in clearedOrders:
                print(c)
            print("For asset {}, the clearing price is {}.".format(asset,clearedPrice))
        # plot graph
        if graph_verbose:
            plt.title("Asset: " + asset)
            plt.show()

    elif matching == 1:
        # sort bids and asks
        # bids are sorted by volume (des)
        bids.sort(key=attrgetter("volume"), reverse=True)
        # asks are sorted by volume (des)
        asks.sort(key=attrgetter("volume"), reverse=True)

        # print volumes
        if graph_verbose:
            plt = volume_plot(bids, asks)
        # perform volume matching
        clearedOrders = volume_matching(bids, asks)

        # find the clearing price from somewhere else (get random here)
        if clearedOrders:
            clearedPrice = random.choice(range(1,100))

        if verbose:
            # print results
            for c in clearedOrders:
                print(c)
            print("For asset {}, the clearing price is {}.".format(asset,clearedPrice))
        # plot graph
        if graph_verbose:
            plt.suptitle("Asset: " + asset)
            plt.show()

    elif matching == 2:
        # sort bids and asks
        # bids are sorted by price (asc) and then volume (des)
        bids.sort(key=attrgetter("volume"), reverse=True)
        bids.sort(key=attrgetter("price"))
        # asks are sorted by price (asc) and then volume (des)
        asks.sort(key=attrgetter("volume"), reverse=True)
        asks.sort(key=attrgetter("price"))

        # print supply and demand curves
        if graph_verbose:
            plt = supply_demand_plot(bids, asks)

        # split into volume 1 orders
        singleB = []
        for bid in bids:
            for i in range(bid.volume):
                singleB.append(bid.copy())
                singleB[-1].volume = 1
        singleA = []
        for ask in asks:
            for i in range(ask.volume):
                singleA.append(ask.copy())
                singleA[-1].volume = 1

        # perform maximum volume matching
        totalVol, clearedOrdersSingle = mv(singleB, singleA)

        # recombine orders
        clearedOrders = []
        if clearedOrdersSingle:
            prevB = clearedOrdersSingle[0][0]
            prevA = clearedOrdersSingle[0][1]
            count = 1
            for c in clearedOrdersSingle[1:]:
                if c[0] == prevB and c[1] == prevA:
                    count += 1
                else:
                    p = int((prevA.price + prevB.price)/2)
                    clearedOrders.append((prevB, prevA, count, p))
                    prevB = c[0]
                    prevA = c[1]
                    count = 1
            p = int((prevA.price + prevB.price)/2)
            clearedOrders.append((prevB, prevA, count, p))
            if verbose:
                for c in clearedOrders:
                    print(c)
        # plot graph
        if graph_verbose:
            plt.suptitle("Asset: " + asset)
            plt.show()

    # return price (if applicable) and matched orders
    return clearedPrice, clearedOrders

def supply_demand_plot(bids, asks, mes=False):
    # total volume up to current order
    volS = 0
    volB = 0

    fig, ax = plt.subplots()
    plt.ylabel('Price')
    plt.xlabel('Quantity')
    pr = 0
    for b in bids:
        if pr != 0:
            # vertical line
            ax.plot([volB,volB], [pr,b.price], 'r-')
        # horizontal lines
        line, = ax.plot([volB,volB+b.volume], [b.price,b.price], 'r-')
        if mes:
            ax.plot([volB,volB+b.mes], [b.price,b.price], 'y-')
        volB += b.volume
        pr = b.price
    if bids:
        line.set_label('Demand')
    pr = 0
    for s in asks:
        if pr != 0:
            # vertical line
            ax.plot([volS,volS], [pr,s.price], 'b-')
        # horizontal lines
        line, = ax.plot([volS,volS+s.volume], [s.price,s.price], 'b-')
        if mes:
            min, = ax.plot([volS,volS+s.mes], [s.price,s.price], 'y-')
        volS += s.volume
        pr = s.price
    if asks:
        line.set_label('Supply')
        if mes:
            min.set_label('Minimum Quantity')
    if bids or asks:
        plt.legend()
    return plt

def periodic_auction(bids, asks):
    cleared = []
    remaining = True

    if asks:
        best_ask = asks[0]
    else:
        remaining = False
    if bids:
        best_bid = bids[0]
    else:
        remaining = False
    # sell price: will sell at this price and more,
    # buy price:  will buy at this price and less
    # therefore      sell price <= buy price
    while remaining and best_ask.price <= best_bid.price:
        # find smallest volume, delete that and remove that much from the other
        # ask has smaller volume
        if best_ask.volume < best_bid.volume:
            cleared.append((best_bid.copy(),best_ask.copy(),best_ask.volume))
            asks.pop(0)
            best_bid.volume -= best_ask.volume
            if asks:
                best_ask = asks[0]
            else:
                remaining = False
        # bid has smaller volume
        elif best_ask.volume > best_bid.volume:
            cleared.append((best_bid.copy(),best_ask.copy(),best_bid.volume))
            bids.pop(0)
            best_ask.volume -= best_bid.volume
            if bids:
                best_bid = bids[0]
            else:
                remaining = False
        # equal volume, delete both
        else:
            cleared.append((best_bid.copy(),best_ask.copy(),best_bid.volume))
            asks.pop(0)
            bids.pop(0)
            if asks:
                best_ask = asks[0]
            else:
                remaining = False
            if bids:
                best_bid = bids[0]
            else:
                remaining = False
    # find clearing price
    if cleared: # check if any orders are cleared
        if bids and asks: # none empty => midprice
            cPrice = round((cleared[-1][0].price + cleared[-1][1].price)/2)
        elif bids: # asks empty => bids price
            cPrice = cleared[-1][0].price
        elif asks: # bids empty => asks price
            cPrice = cleared[-1][1].price
        else: # both empty => midprice
            cPrice = round((cleared[-1][0].price + cleared[-1][1].price)/2)
    else:
        cPrice = -1

    return cleared, cPrice

def volume_plot(bids, asks):
    if bids and asks:
        m = max(bids[0].volume, asks[0].volume)
    elif bids:
        m = bids[0].volume
    elif asks:
        m = asks[0].volume
    else:
        m = 1
    m = int(1.1*m)
    b_mes = []
    b_vol = []
    if (len(asks) > len(bids)):
        b_off = len(asks)-len(bids)
        for i in range(b_off):
            b_mes.append(0)
            b_vol.append(0)
    else:
        b_off = 0
    for b in reversed(bids):
        b_mes.append(b.mes)
        b_vol.append(b.volume)

    a_mes = []
    a_vol = []
    for a in asks:
        a_mes.append(a.mes)
        a_vol.append(a.volume)
    if (len(bids) > len(asks)):
        a_off = len(bids) - len(asks)
        for i in range(a_off):
            a_mes.append(0)
            a_vol.append(0)
    else:
        a_off = 0

    fig, axes = plt.subplots(nrows=1, ncols=2)
    ax0, ax1 = axes.flatten()

    if bids:
        ax0.bar(range(len(bids)+b_off), b_vol, label='volume')
        ax0.bar(range(len(bids)+b_off), b_mes, label='mes')
        ax0.legend()
    ax0.set_title('bids')
    ax0.set_ylim([0,m])

    if asks:
        ax1.bar(range(len(asks)+a_off), a_vol, label='volume')
        ax1.bar(range(len(asks)+a_off), a_mes, label='mes')
        ax1.legend()
    ax1.set_title('asks')
    ax1.set_ylim([0,m])

    fig.tight_layout()
    return plt

def volume_matching(orBids, orAsks):
    cleared = []
    bids = orBids.copy()
    asks = orAsks.copy()

    for b in bids:
        # remove used asks
        asks[:] = [a for a in asks if a.volume >= a.mes]
        # early termination
        if not asks:
            break

        for a in asks:
            if b.volume < b.mes:
                # bid consumed, go to next bid
                break
            if b.mes > a.volume or a.mes > b.volume:
                # not compatible, go to next ask
                continue
            # can match current ask with current bid
            vol = min(a.volume, b.volume)
            cleared.append((b.copy(),a.copy(),vol))
            b.volume -= vol
            a.volume -= vol

    return cleared

### Maximizing Matching Functions ###

def poll(lst):
    if lst:
        return lst.pop(0)
    else:
        return False

# bids and asks are ordered in ascending price
def find_max_vol(bids, asks):
    qmin = 0
    a = poll(asks)
    if a:
        b = poll(bids)
        while b and b.price < a.price:
            b = poll(bids)
        qd = 0
        q = 0
        while b:
            if a and a.price <= b.price:
                q = q + a.volume
                a = poll(asks)
            else:
                q = q - b.volume
                qmin = min(qmin, q)
                qd = qd + b.volume
                b = poll(bids)
        qmin = qmin + qd
    return qmin

# bids and asks are ordered in ascending price
def mv(bids, asks):
    q = find_max_vol(bids.copy(), asks.copy())
    #print(q)
    m = []
    for i in range(q):
        r_pos = len(bids)-q+i
        m.append((bids[r_pos], asks[i]))
    return q, m
