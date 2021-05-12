from helper import *
import json
from web3 import Web3, HTTPProvider
import sys
import os
from ecies.utils import generate_key
from ecies import encrypt, decrypt
import time
import random
import hashlib
from operator import attrgetter
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------

# path to parent directory
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# contract path
contract_path = parent_path+'/truffle/build/contracts/darkPool.json'
try:
    f=open('./data/address.dat', 'r')
    contractAddress = Web3.toChecksumAddress(f.read())
    f.close()
    print("Contract Address:", contractAddress)
except:
    sys.exit("Error: The smart contract needs to be deployed.")

# open compiled file and get abi
truffleFile = json.load(open(contract_path))
abi = truffleFile['abi']

# setup web3 instance using testnet
f=open('./data/endpoint.dat', 'r')
testnet_endpoint = f.read()
f.close()
w3 = Web3(HTTPProvider(testnet_endpoint))
if w3.isConnected():
    print("Web3 Connected")
else:
    sys.exit("Error: Couldn't connect to the blockchain via web3")

# contract interface
darkPool = w3.eth.contract(address=contractAddress, abi=abi)

# ------------------------------------------------------------------------------
# Parameters
# ------------------------------------------------------------------------------

# general parameters/variables, needed everywhere
matchings = ["Periodic", "Volume", "MV"] # list of available matching modes
assets = ['g','t','f'] # list of tradable assets
matched = False
trades_received = []
valid_asks = {}
valid_bids = {}
for a in assets:
    valid_asks[a] = []
    valid_bids[a] = []
total_gas = 0
loops = 0

# specific parameters, should be set for particular usecase
verbose = True
gas_verbose = True
graph_verbose = False

# ------------------------------------------------------------------------------
# Command line arguments
# ------------------------------------------------------------------------------

if len(sys.argv) == 2:
    # find the address and key
    registered = []
    key_file = './data/key_client_' + sys.argv[1] + '.dat'
    f=open(key_file, 'r')
    key = f.read()
    f.close()
    addr = w3.eth.account.privateKeyToAccount(key).address
    order_file = './data/client_order_'+ sys.argv[1] +'.dat'
else:
    sys.exit("Error: Client number must be specified.")

# ------------------------------------------------------------------------------
# Contract function calls
# ------------------------------------------------------------------------------

if verbose:
    print("My address is:", addr)

while (True):

    if verbose:
        print("--------------------------------------------------------------------------------------------")
        print("Waiting for the next trading day. Please add new order (either through script or front-end).")

    phase = darkPool.functions.phase().call()
    while phase != 1:
        # wait for trading phase
        time.sleep(1)
        # get phase and expiration
        phase = darkPool.functions.phase().call()
        expiration = darkPool.functions.expiration().call()

    # save block at the start of the trading day
    start = w3.eth.blockNumber

    try:
        # open file to read transaction
        f=open(order_file, 'r')
        order_string = f.read()
        f.close()
        os.remove(order_file)
    except:
        # file is empempty transaction
        order_string = "None"

    if verbose:
        print("At Trading phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))

    # get auction mode from contract
    matching = darkPool.functions.auctionMode().call()
    if verbose:
        print("Matching Algorithm:", matchings[matching])

    # get assigned public key from contract
    pk = darkPool.functions.us_pk(addr).call()
    if pk == b'':
        sys.exit("Error: Not registered on the smart contract, contact operator to register.")
    elif verbose:
        print("My assigned public key is:", pk)

    if verbose:
        print("My order is:", order_string)

    # generate random 32 byte nonce
    nonce = os.urandom(32)
    # append nonce and encode order string
    order_bytes = order_string.encode('utf-8') + nonce
    # encrypt order bytes
    order_ciphertext = encrypt(pk, order_bytes)
    # hash ciphertext
    order_hash = hashlib.sha3_256(order_ciphertext).digest()

    # send commitment
    # build transaction
    tx = darkPool.functions.commit_order(order_hash).buildTransaction({
        'from': addr,
        'nonce': w3.eth.getTransactionCount(addr),
        'gas': 6721975, # from truffle docs
        'gasPrice': 100000000000 # from truffle docs
    })
    # sign transaction
    sign_tx = w3.eth.account.signTransaction(tx, key)
    # send the transaction
    tx_hash = w3.eth.sendRawTransaction(sign_tx.rawTransaction)
    # wait for transaction receipt
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=300)

    if verbose:
        print("Order sent.")
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)

    # wait for reveal phase
    while phase != 2:
        time.sleep(1)
        # get phase and expiration
        phase = darkPool.functions.phase().call()
        expiration = darkPool.functions.expiration().call()

    if verbose:
        print("At Reveal phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))

    # reveal order
    # build transaction
    tx = darkPool.functions.reveal_order(order_ciphertext).buildTransaction({
        'from': addr,
        'nonce': w3.eth.getTransactionCount(addr),
        'gas': 6721975, # from truffle docs
        'gasPrice': 100000000000 # from truffle docs
    })
    # sign transaction
    sign_tx = w3.eth.account.signTransaction(tx, key)
    # send the transaction
    tx_hash = w3.eth.sendRawTransaction(sign_tx.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=300)

    if verbose:
        print("Order revealed.")
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)

    # wait for results phase
    while phase != 4:
        time.sleep(1)
        # get phase and expiration from event
        phase = darkPool.functions.phase().call()
        expiration = darkPool.functions.expiration().call()

    if verbose:
        print("At Results phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))

    # get new published matchings
    matches = darkPool.events.logTrade.getLogs(fromBlock=start)
    for m in matches:
        # get matching details
        buyer = m['args']["buyer"]
        buyerAddr = m['args']["buyerAddr"]
        seller = m['args']["seller"]
        sellerAddr = m['args']["sellerAddr"]
        asset = m['args']['asset']
        vol = m['args']["amount"]
        price = m['args']["price"]
        # add tuple to received trades
        trades_received.append((buyerAddr, sellerAddr, asset, vol, price))
        if verbose:
            print("Matchig: seller {}, buyer {}, asset {}, price {}, volume {}"
              .format(seller, buyer, asset, price, vol))

    '''
    # simulate fraud by adding an extra match
    trades_received.append(('0x1', '0x2', 'g', 1, 1))
    '''
    '''
    # simulate fraud by changing a match
    trades_received[0] = ('0x1', '0x2', 'g', 1, 1)
    '''

    executed = darkPool.events.secretRevealed.getLogs(fromBlock=start)
    # verification of mathes
    for order in executed:
        # extract details
        sender = order['args']['sender']
        commitment = order['args']['commitment']
        ciphertext = order['args']['ciphertext']
        secret = order['args']['secret']

        # check if my order was executed
        if sender == addr:
            matched = True
            if verbose:
                print("My order was executed.")

        # validate commitment
        status, order = validate_commitment(assets, sender, commitment, ciphertext, secret, False)

        if status != 0:
            sys.exit("Error: Invalid order found. Auction verifiaction failed.")
        else:
            # order is valid
            #if verbose:
            #    print("Order is valid.")
            # check type and add to appropriate list
            if order.type == 's':
                valid_asks[order.asset].append(order.copy())
            elif order.type == 'b':
                valid_bids[order.asset].append(order.copy())

    # add my own order in valid if not executed
    if not matched and order_string != "None":
        l = order_string.split(",")
        my_order = Order(addr, l[0], l[1], int(l[2]), int(l[3]), int(l[4]), '')
        if my_order.type == 'b':
            valid_bids[my_order.asset].append(my_order.copy())
        elif my_order.type == 's':
            valid_asks[my_order.asset].append(my_order.copy())

    # for each asset, perform matching locally
    for a in assets:
        bids = valid_bids[a]
        asks = valid_asks[a]

        clearedPrice, clearedOrders = match(matching, a, bids, asks, verbose, graph_verbose)

        for c in clearedOrders:
            bAddr = c[0].client
            sAddr = c[1].client
            vol = c[2]
            # in MV mode, each match has a different price
            if matching == 2:
                clearedPrice = c[3]
            calculated_trade = (bAddr, sAddr, a, vol, clearedPrice)
            # search for this trade in the received trades
            found = False
            for trade in trades_received:
                # in Volume mode price is sourced from elswhere
                # so just use the one in the matching
                if matching == 1:
                    calculated_trade = (bAddr, sAddr, a, vol, trade[4])
                if calculated_trade == trade:
                    found = True
                    # remove this trade since it was found
                    trades_received.remove(trade)
                    break
            if not found:
                # claim fraud
                # build transaction
                tx = darkPool.functions.claim_fraud().buildTransaction({
                    'from': addr,
                    'nonce': w3.eth.getTransactionCount(addr),
                    'gas': 6721975, # from truffle docs
                    'gasPrice': 100000000000 # from truffle docs
                })
                # sign transaction
                sign_tx = w3.eth.account.signTransaction(tx, key)
                # send the transaction
                tx_hash = w3.eth.sendRawTransaction(sign_tx.rawTransaction)
                tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=300)

                sys.exit("Error: Invalid matching found. Auction verifiaction failed.")
            #elif verbose:
            #    print("Valid matching.")

    # check if at the end there are additional matchings in the list
    if trades_received:
        # build transaction
        tx = darkPool.functions.claim_fraud().buildTransaction({
            'from': addr,
            'nonce': w3.eth.getTransactionCount(addr),
            'gas': 6721975, # from truffle docs
            'gasPrice': 100000000000 # from truffle docs
        })
        # sign transaction
        sign_tx = w3.eth.account.signTransaction(tx, key)
        # send the transaction
        tx_hash = w3.eth.sendRawTransaction(sign_tx.rawTransaction)
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=300)

        sys.exit("Error: Unaccounted matchings found. Auction verifiaction failed.")
    elif verbose:
        print("Auction verification succesful. No fraud detected.")

    if gas_verbose:
        print("Total gas used during this trading day:", total_gas)

    # wait for registration phase
    while phase != 0:
        time.sleep(1)
        # get phase and expiration from event
        phase = darkPool.functions.phase().call()
        expiration = darkPool.functions.expiration().call()

    fraud = darkPool.events.fraud_filter.getLogs(fromBlock=start)
    for f in fraud:
        print("Warning: Fraud claimed by", f['args']['claimer'])
