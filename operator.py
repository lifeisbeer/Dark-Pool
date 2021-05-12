from helper import *
import json
from web3 import Web3, HTTPProvider
import sys
from ecies.utils import generate_key
from ecies import decrypt
import time
import random
import hashlib
from operator import attrgetter
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------

# contract details
contract_path = './truffle/build/contracts/darkPool.json'
try:
    f=open('./data/address.dat', 'r')
    contractAddress = f.read()
    f.close()
    print("Contract Address:", contractAddress)
except:
    sys.exit("Error: The smart contract needs to be deployed.")

# open compiled file and get abi
truffleFile = json.load(open(contract_path))
abi = truffleFile['abi']

# setup web3 instance using ganache
ganache_url = "http://127.0.0.1:8545"
w3 = Web3(HTTPProvider(ganache_url))
if w3.isConnected():
    print("Web3 Connected")
else:
    sys.exit("Error: Couldn't connect to the blockchain via web3.")

# set default account
w3.eth.defaultAccount = w3.eth.accounts[0]
# contract interface
darkPool = w3.eth.contract(address=contractAddress, abi=abi)

# ------------------------------------------------------------------------------
# Parameters
# ------------------------------------------------------------------------------

# general parameters/variables, needed everywhere
matchings = ["Periodic", "Volume", "MV"] # list of available assets
assets = ['g','t','f'] # list of tradable assets
loop_count = 0
addr2keys = {}
addr2name = {}
invalid_addr = []
orders = {}
valid_asks = {}
valid_bids = {}
for a in assets:
    valid_asks[a] = []
    valid_bids[a] = []

# specific parameters, should be set for particular usecase
client_num = 3
registration = True
clear = True
max_loops = 1
duration = 2
total_gas = 0
verbose = True
gas_verbose = True
graph_verbose = True

# ------------------------------------------------------------------------------
# Command line arguments
# ------------------------------------------------------------------------------

if len(sys.argv) >= 2:
    matching = int(sys.argv[1]) # [0,1,2]
    if len(sys.argv) >= 3:
        client_num = int(sys.argv[2]) # [1,...]
        if len(sys.argv) >= 4:
            max_loops = int(sys.argv[3]) # [1,...]
            if len(sys.argv) == 5:
                duration = int(sys.argv[4]) # [2,...]
            else:
                sys.exit("Error: Wrong number of arguments (mandatory: auction mode | optional: client number, trading days, duration).")
else:
    sys.exit("Error: Wrong number of arguments (mandatory: auction mode | optional: client number, trading days, duration).")

# ------------------------------------------------------------------------------
# Contract function calls
# ------------------------------------------------------------------------------

# create a filter to be notified when we are in a new phase
phase_filter = darkPool.events.startPhase.createFilter(fromBlock="latest")

# read client addresses
registered = []
count = 0
f = open('./data/registered.dat', "r")
for r in f:
    # remove new line
    addr = r[:-1]
    registered.append(addr)
    addr2name[addr] = str(count)
    count += 1
f.close()

if registration:
    # register some clients
    tx_hashes = []
    for i in range(client_num):
        # this address will be send to the operator by the client in the final
        # application, but for now we will just use one of the existing addresses
        addr = registered[i]
        # generate a key pair and store
        addr2keys[addr] = generate_key()
        pk = addr2keys[addr].public_key.format(True)
        # send the address and the corresonding public key to the contract
        tx_hash = darkPool.functions.register_client(addr, pk).transact()
        tx_hashes.append(tx_hash)
    # wait for all transactions to go through
    for i in range(len(tx_hashes)):
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i])
        if verbose:
            print("Client", i, "registered with address:", registered[i])
        if gas_verbose:
            total_gas += tx_receipt.gasUsed
            print("Gas used:", tx_receipt.gasUsed)
    if gas_verbose:
        print("Total gas used during registration:", total_gas)

# ---Start of the trading day---

while loop_count < max_loops:
    loop_count += 1
    total_gas = 0

    # initiate trading phase
    print("------------------------------------------------------------------------------")
    print("Start of a new trading day({}): ".format(loop_count))
    print("------------------------------------------------------------------------------")

    tx_hash = darkPool.functions.trading_phase(duration, matching).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    if verbose:
        print("Matching Algorithm:", matchings[matching])

    event = phase_filter.get_new_entries()
    expiration = event[0]['args']['expirationTime']
    if verbose:
        print("At Trading phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)

    # wait until the expiration of the trading phase
    while w3.eth.blockNumber < expiration:
        time.sleep(1)

    # initiate reveal phase
    tx_hash = darkPool.functions.reveal_phase(duration).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    event = phase_filter.get_new_entries()
    expiration = event[0]['args']['expirationTime']
    if verbose:
        print("At Reveal phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)
    # wait until the expiration of the reveal phase
    while w3.eth.blockNumber < expiration:
        time.sleep(1)

    # initiate calculation phase
    tx_hash = darkPool.functions.calc_phase().transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    event = phase_filter.get_new_entries()
    if verbose:
        print("At Calculation phase. Current block: {}.".format(w3.eth.blockNumber))
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)

    # read commitments and ciphertext for each client
    for i in range(client_num):
        # get client address from server memory
        addr = registered[i]
        # get order from contract
        order = darkPool.functions.orders(addr).call()
        #print(order)
        commitment = order[0]
        ciphertext = order[1]
        # get keys from memory
        secret = addr2keys[addr].secret

        # check if client submited an order
        if len(commitment) == 0:
            if verbose:
                print("Client", i, "did not submit an order.")
        else:
            # validate commitment
            status, order = validate_commitment(assets, addr, commitment, ciphertext, secret, True)

            if status == 0:
                # order is valid
                if verbose:
                    print("Client's {} order: {}".format(i, order))
                # calculate shared secret and append to order
                order.secret = shared_secret(secret, ciphertext)
                # check type and add to appropriate list
                orders[addr] = order.copy()
                if order.type == 's':
                    valid_asks[order.asset].append(order.copy())
                elif order.type == 'b':
                    valid_bids[order.asset].append(order.copy())
            elif status == 1:
                # order is empty
                if verbose:
                    print("Client's {} order is empty.".format(i))
            else:
                # invalid order
                invalid_addr.append(addr)
                if verbose:
                    print("Client", i, order)

    if verbose:
        print("Addresses that send an invalid order:", invalid_addr)
        #print("Orders:", orders)
        #print("Valid asks:", valid_asks)
        #print("Valid bids:", valid_bids)

    # for each asset, perform matching
    for a in assets:
        bids = valid_bids[a]
        asks = valid_asks[a]

        clearedPrice, clearedOrders = match(matching, a, bids, asks, verbose, graph_verbose)

        # ---Mathing Done---
        # publish matched orders
        tx_hashes = []
        #print(clearedOrders)
        for c in clearedOrders:
            bAddr = c[0].client
            bSK = c[0].secret
            bName = addr2name[bAddr]
            sAddr = c[1].client
            sSK = c[1].secret
            sName = addr2name[sAddr]
            vol = c[2]
            if matching == 2:
                clearedPrice = c[3]
            # operator publishes matched orders
            tx_hash = darkPool.functions.reveal_match(a, bAddr, bSK, bName,
                                sAddr, sSK, sName, vol, clearedPrice).transact()
            #tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            tx_hashes.append(tx_hash)
        for tx_hash in tx_hashes:
            tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            if verbose:
                print("Matching published.")
            if gas_verbose:
                total_gas += tx_receipt.gasUsed
                print("Gas used:", tx_receipt.gasUsed)

    '''
    # operator publishes fake match
    tx_hash = darkPool.functions.reveal_match('a', w3.eth.accounts[2], addr2keys[w3.eth.accounts[2]].secret, 'a',
                        w3.eth.accounts[3], addr2keys[w3.eth.accounts[3]].secret, 'b', 100, 100).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    '''

    # initiate results phase
    tx_hash = darkPool.functions.res_phase(duration).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    event = phase_filter.get_new_entries()
    expiration = event[0]['args']['expirationTime']
    if verbose:
        print("At Results phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)

    # wait until the expiration of the results phase
    while w3.eth.blockNumber < expiration:
        time.sleep(1)

    # initiate registration phase
    tx_hash = darkPool.functions.reg_phase().transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    event = phase_filter.get_new_entries()
    if verbose:
        print("At Registration phase. Current block: {}.".format(w3.eth.blockNumber))
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)

'''
    # assign new keys to clients that made a trade
    tx_hashes = []
    for addr in matched_addr:
        # generate a key pair and store
        addr2keys[addr] = generate_key()
        pk = addr2keys[addr].public_key.format(True)

        # send the address and the corresonding public key to the contract
        txhash = darkPool.functions.register_client(addr, pk).transact()
        tx_hashes.append(tx_hash)

        if verbose:
            print("Client {} assigned new public key".format(addr2name[addr]))
    # wait for all transactions to go through
    for i in range(len(tx_hashes)):
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i])
'''

    # reset contract
    tx_hashes = []
    for i in range(client_num):
        addr = registered[i]
        tx_hash = darkPool.functions.remove_order(addr).transact()
        tx_hashes.append(tx_hash)
    # wait for all transactions to go through
    for i in range(len(tx_hashes)):
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i])
        if verbose:
            print("Client", i+1, "order deleted from contract.")
        if gas_verbose:
            total_gas += tx_receipt.gasUsed
            print("Gas used:", tx_receipt.gasUsed)

    # reset server memory
    invalid_addr = []
    orders = {}
    for a in assets:
        valid_asks[a] = []
        valid_bids[a] = []

    # check that the contract variables were reset correctly
    for i in range(client_num):
        addr = registered[i]
        assert darkPool.functions.orders(addr).call()[0] == b'', "Commitment not reset correctly."
        assert darkPool.functions.orders(addr).call()[1] == b'', "Ciphertext not reset correctly."
        assert darkPool.functions.orders(addr).call()[2] == b'', "Secret-key not reset correctly."
    if verbose:
        print("Contract was reset correctly and is ready for reuse on the next trading day.")
    if gas_verbose:
        print("Total gas used during this trading day:", total_gas)

if clear:
    total_gas = 0
    # reset client accounts
    tx_hashes = []
    for i in range(client_num):
        addr = registered[i]
        tx_hash = darkPool.functions.remove_client(addr).transact()
        tx_hashes.append(tx_hash)
    # wait for all transactions to go through
    for i in range(len(tx_hashes)):
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i])
        if verbose:
            print("Client", i+1, "deleted from contract.")
        if gas_verbose:
            total_gas += tx_receipt.gasUsed
            print("Gas used:", tx_receipt.gasUsed)
    if gas_verbose:
        print("Total gas used during reset:", total_gas)

    # check that the client accounts were reset correctly
    for i in range(client_num):
        addr = registered[i]
        assert darkPool.functions.us_pk(addr).call() == b'', "Public-key not reset correctly."
    if verbose:
        print("All client accounts were deleted correctly.")

if verbose:
    print("Server stoped, contract is still available when the server restarts.")
