from helper import *
import json
from web3 import Web3, HTTPProvider, WebsocketProvider
import sys
from ecies.utils import generate_key
import os
from ecies import encrypt, decrypt
import time
import random
import hashlib
from operator import attrgetter
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------
# Parameters
# ------------------------------------------------------------------------------

# general parameters
assets = ['g']#,'t','f'] # list of tradable assets
matchings = ["Periodic", "Volume", "MV"] # list of matching modes
verbose = True
stats_verbose = True
gas_verbose = False
graph_verbose = False
total_gas = 0

# kept in client memory
ciphertexts = {}

# kept in server memory
addr2keys = {}
addr2name = {}
# experiment parameters
matching = 0
max_client_num = 1000
client_start = 100
client_step = 100
duration = 1

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------

# Create stats file
stats = open('stats_2_3.dat', 'w')

# contract details
contract_path = './truffle/build/contracts/darkPool.json'
contractAddress = ''

# open compiled file and get abi
truffleFile = json.load(open(contract_path))
abi = truffleFile['abi']

# setup web3 instance using ganache
ganache_url = "http://127.0.0.1:8545"
w3 = Web3(HTTPProvider(ganache_url))
#ganache_url = 'ws://localhost:8545'
#w3 = Web3(WebsocketProvider(ganache_url))
if w3.isConnected():
    print("Web3 Connected")
else:
    sys.exit("Couldn't connect to the blockchain via web3")
# set default account
w3.eth.defaultAccount = w3.eth.accounts[0]
# setup other accounts
for i in range(1, max_client_num+1):
    addr2name[w3.eth.accounts[i]] = str(i)

# if contract is not deployed, deploy it and return address
if not contractAddress:
    contractAddress = deploy_contract(w3, contract_path)

# contract interface
darkPool = w3.eth.contract(address=contractAddress, abi=abi)

# ------------------------------------------------------------------------------
# Contract function calls
# ------------------------------------------------------------------------------

# create a filter to be notified when a matching is published
# this event(log) contains 4 fields: 'buyer', 'seller', 'amount' and 'price'
match_filter = darkPool.events.logTrade.createFilter(fromBlock="latest")

if stats_verbose:
    print("Start. At Block:", w3.eth.blockNumber)
    stats.write('Start: ')
    stats.write(str(max_client_num))
    stats.write(' ')
    stats.write(str(w3.eth.blockNumber))
    stats.write(' ')

# register some clients
tx_hashes = []
for i in range(1, max_client_num+1):
    # this address will be send to the operator by the client in the final
    # application, but for now we will just use one of the existing addresses
    addr = w3.eth.accounts[i]
    # generate a key pair and store
    addr2keys[addr] = generate_key()
    pk = addr2keys[addr].public_key.format(True)
    # send the address and the corresonding public key to the contract
    tx_hash = darkPool.functions.register_client(addr, pk).transact()
    tx_hashes.append(tx_hash)
# wait for all transactions to go through
for i in range(len(tx_hashes)):
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i], timeout=1200)
    total_gas += tx_receipt.gasUsed
    #if verbose:
    #    print("Client {} registered with address {} at block {}".format(i+1,w3.eth.accounts[i+1],tx_receipt["blockNumber"]))
    if gas_verbose:
        print("Gas used:", tx_receipt.gasUsed)

if stats_verbose:
    print("Initial registration done. At Block:", w3.eth.blockNumber)
    stats.write(str(w3.eth.blockNumber))
    stats.write(' ')
    stats.write(str(total_gas))
    stats.write('\n')

if gas_verbose:
    print("Total gas used during initial registration:", total_gas)
total_gas = 0

# run multiple experiments varying the client number every time
for client_num in range(client_start, max_client_num+1, client_step):

    interaction_count = 0

    if stats_verbose:
        print("New trading day. Clients:", client_num,". At Block:", w3.eth.blockNumber)
        stats.write(str(client_num))
        stats.write(' ')
        stats.write(str(w3.eth.blockNumber))
        stats.write(' ')

    # initiate trading phase
    tx_hash = darkPool.functions.trading_phase(duration, matching).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=1200)
    total_gas += tx_receipt.gasUsed
    interaction_count += 1

    expiration = darkPool.functions.expiration().call()
    if verbose:
        print("------------------------------------------------------------------------------")
        print("At Trading phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))
        print("Auction Matching type:", matchings[matching])
    if gas_verbose:
        print("Gas used:", tx_receipt.gasUsed)

    # now the clients that wish to transact will send in their orders
    # for this demonstration we will call orders from different existing
    # ganache accounts from this script

    # the register clients send their commitments
    tx_hashes = []
    for i in range(1, client_num+1):
        addr = w3.eth.accounts[i]
        # order is a comma-separated string consisting of
        # 1) char: direction, b for buy & s for sell
        # 2) char: instrument, representing tradable asset
        # 3) int:  limit price (in pence)
        # 4) int:  size of order
        # 5) int:  minimum order execution size (mes)
        # 6) int:  random nonce
        # eg "s,t,100,1005,50,1234" represents a sell order for asset t with
        #    volume 100, price 10.5 each and minimum order execution size 50
        # order will be provided by the client, generate random for this test
        order = create_random_order(assets, 100, 100)
        # generate random 32 byte nonce
        nonce = os.urandom(32)
        '''
        # for this demonstration, client 3 will send an invalid order
        if i == 3:
            order.type = 'a' # invalid type
            #order.price = -1 # invalid price
            #order.volume = -1 # invalid volume
            #order.mes = order.volume + 1 # invalid mes
            print("Client 3 will send an invalid order.")
        '''
        # format order into string
        order_string = "{},{},{},{},{}".format(order.type,order.asset,
                       order.price,order.volume,order.mes)
        '''
        # for this demonstration, client 3 will send an empty order
        if i == 3:
            order_string = "None"
        '''
        #if verbose:
        #    print("Client {} send order: {}".format(i, order_string))
        # append nonce and encode order string
        order_bytes = order_string.encode('utf-8') + nonce
        # get assigned public key from contract
        pk = darkPool.functions.us_pk(addr).call()
        # encrypt order bytes
        ciphertext = encrypt(pk, order_bytes)
        ciphertexts[addr] = ciphertext
        # hash ciphertext
        hash = hashlib.sha3_256(ciphertext).digest()
        # send hash (commitment)
        tx_hash = darkPool.functions.commit_order(hash).transact(
                  {'from':w3.eth.accounts[i]})
        tx_hashes.append(tx_hash)
        # wait for transaction receipt
        #tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    # wait for all transactions to go through
    for i in range(len(tx_hashes)):
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i], timeout=1200)
        total_gas += tx_receipt.gasUsed
        interaction_count += 1
        if gas_verbose:
            print("Gas used:", tx_receipt.gasUsed)

    '''
    # for this demonstration, client 1 will cancel their commitment
    tx_hash = darkPool.functions.cancel_order().transact(
              {'from':w3.eth.accounts[1]})
    ciphertexts.pop(w3.eth.accounts[1])
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if verbose:
        print("Client 1 canceled order")
    if gas_verbose:
        total_gas += tx_receipt.gasUsed
        print("Gas used:", tx_receipt.gasUsed)
    '''

    # the operator waits until (at least) the expiration of the trading phase
    while w3.eth.blockNumber < expiration:
        time.sleep(10)

    # operator initiates reveal phase
    tx_hash = darkPool.functions.reveal_phase(duration).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=1200)
    total_gas += tx_receipt.gasUsed
    interaction_count += 1

    expiration = darkPool.functions.expiration().call()
    if verbose:
        print("At Reveal phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))
    if gas_verbose:
        print("Gas used:", tx_receipt.gasUsed)

    '''
    #for demonstration, client 2 will send ciphertext that doesn't match
    ciphertexts[w3.eth.accounts[2]] = ciphertexts[w3.eth.accounts[3]]
    print("Client 2 will send ciphertext that doesn't match its commitment")
    '''

    # the clients reveal their orders to operator
    tx_hashes = []
    for i in range(1, client_num+1):
        addr = w3.eth.accounts[i]
        if addr in ciphertexts.keys():
            # each client knows its own ciphertext, here we retreive from list
            ciphertext = ciphertexts[addr]
            # send ciphertext
            tx_hash = darkPool.functions.reveal_order(ciphertext).transact(
                      {'from':w3.eth.accounts[i]})
            tx_hashes.append(tx_hash)
            #tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    # wait for all transactions to go through
    for i in range(len(tx_hashes)):
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i], timeout=1200)
        total_gas += tx_receipt.gasUsed
        interaction_count += 1
        #if verbose:
        #    print("Client", i+1, "revealed order")
        if gas_verbose:
            print("Gas used:", tx_receipt.gasUsed)

    # the operator waits until (at least) the expiration of the reveal phase
    while w3.eth.blockNumber < expiration:
        time.sleep(10)

    # operator initiates calculation phase
    tx_hash = darkPool.functions.calc_phase().transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=1200)
    total_gas += tx_receipt.gasUsed
    interaction_count += 1

    if verbose:
        print("At Calculation phase. Current block: {}.".format(w3.eth.blockNumber))
    if gas_verbose:
        print("Gas used:", tx_receipt.gasUsed)

    # initialise
    invalid_addr = []
    orders = {}
    valid_asks = {}
    valid_bids = {}
    for a in assets:
        valid_asks[a] = []
        valid_bids[a] = []

    # operator reads commitments and ciphertext for each client
    for i in range(1, client_num+1):
        # get client address from server memory
        addr = w3.eth.accounts[i]
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
                print("Client", i, "did not submit an order")
        else:
            # validate commitment
            status, order = validate_commitment(assets, addr, commitment, ciphertext, secret, True)

            if status != 0:
                invalid_addr.append(addr)
                if verbose:
                    print("Client", i, order)
            else:
                # order is valid
                #if verbose:
                #    print("Client's {} order: {}".format(i, order))
                # calculate shared secret and append to order
                order.secret = shared_secret(secret, ciphertext)
                # check type and add to appropriate list
                orders[addr] = order.copy()
                if order.type == 's':
                    valid_asks[order.asset].append(order.copy())
                elif order.type == 'b':
                    valid_bids[order.asset].append(order.copy())

    if verbose:
        print("Addresses that send an invalid order:", invalid_addr)
        #print(orders)
        #print(valid_asks)
        #print(valid_bids)

    # for each asset, perform matching
    for a in assets:
        bids = valid_bids[a]
        asks = valid_asks[a]

        clearedPrice, clearedOrders = match(matching, a, bids, asks, False, graph_verbose)

        # publish matched orders
        tx_hashes = []
        for c in clearedOrders:
            bAddr = c[0].client
            bSK = c[0].secret
            bName = addr2name[bAddr]
            sAddr = c[1].client
            sSK = c[1].secret
            sName = addr2name[sAddr]
            vol = c[2]
            if matching == 2: clearedPrice = c[3]

            # operator publishes matched orders
            tx_hash = darkPool.functions.reveal_match(a, bAddr, bSK, bName,
                                sAddr, sSK, sName, vol, clearedPrice).transact()
            #tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            tx_hashes.append(tx_hash)

        for tx_hash in tx_hashes:
            tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=1200)
            total_gas += tx_receipt.gasUsed
            interaction_count += 1
            if gas_verbose:
                print("Gas used:", tx_receipt.gasUsed)

    # operator initiates results phase
    tx_hash = darkPool.functions.res_phase(0).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=1200)
    total_gas += tx_receipt.gasUsed
    interaction_count += 1

    expiration = darkPool.functions.expiration().call()
    if verbose:
        print("At Results phase. Current block: {}, Expiration: {}.".format(w3.eth.blockNumber, expiration))
    if gas_verbose:
        print("Gas used:", tx_receipt.gasUsed)

    # get new published matchings
    matches = match_filter.get_new_entries()

    if stats_verbose:
        print("Number of matches:", len(matches))
        stats.write(str(len(matches)))
        stats.write(' ')
    '''
    for m in matches:
        # get matching details
        buyer = m['args']["buyer"]
        seller = m['args']["seller"]
        asset = m['args']['asset']
        vol = m['args']["amount"]
        price = m['args']["price"]
        if verbose:
            print("Matchig between seller {} and buyer {}, for asset {} with price {} and volume {}"
              .format(seller, buyer, asset, price, vol))
    '''

    # operator initiates registration phase
    tx_hash = darkPool.functions.reg_phase().transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=1200)
    total_gas += tx_receipt.gasUsed
    interaction_count += 1

    if verbose:
        print("At Registration phase. Current block: {}.".format(w3.eth.blockNumber))
    if gas_verbose:
        print("Gas used:", tx_receipt.gasUsed)

    # delete orders
    tx_hashes = []
    for i in range(1, client_num+1):
        addr = w3.eth.accounts[i]
        tx_hash = darkPool.functions.remove_order(addr).transact()
        tx_hashes.append(tx_hash)
    # wait for all transactions to go through
    for i in range(len(tx_hashes)):
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i], timeout=1200)
        total_gas += tx_receipt.gasUsed
        interaction_count += 1
        #if verbose:
        #    print("Client {} order deleted from contract at block {}".format(i+1,tx_receipt["blockNumber"]))
        if gas_verbose:
            print("Gas used:", tx_receipt.gasUsed)

    if stats_verbose:
        print("End of trading day. At Block:", w3.eth.blockNumber)
        stats.write(str(w3.eth.blockNumber))
        stats.write(' ')
        stats.write(str(total_gas))
        stats.write(' ')
        stats.write(str(interaction_count))
        stats.write('\n')

    if gas_verbose:
        print("Total gas used during this trading day:", total_gas)
    if verbose:
        print("------------------------------------------------------------------------------")
    total_gas = 0

# Close stats file
stats.close()

'''
# delete all clients
tx_hashes = []
for i in range(1, client_num+1):
    addr = w3.eth.accounts[i]
    addr2keys.pop(addr)
    tx_hash = darkPool.functions.remove_client(addr).transact()
    tx_hashes.append(tx_hash)
# wait for all transactions to go through
for i in range(len(tx_hashes)):
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i], timeout=1200)
    total_gas += tx_receipt.gasUsed
    if verbose:
        print("Client", i+1, "deleted from contract")
    if gas_verbose:
        print("Gas used:", tx_receipt.gasUsed)
if gas_verbose:
    print("Total gas used during client deletion:", total_gas)
total_gas = 0

# re-register all clients
tx_hashes = []
for i in range(0, client_num):
    addr = w3.eth.accounts[i]
    # generate a key pair and store
    addr2keys[addr] = generate_key()
    pk = addr2keys[addr].public_key.format(True)
    # send the address and the corresonding public key to the contract
    tx_hash = darkPool.functions.register_client(addr, pk).transact()
    tx_hashes.append(tx_hash)
# wait for all transactions to go through
for i in range(len(tx_hashes)):
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hashes[i])
    print("Client", i+1, "registered with address:", w3.eth.accounts[i+1])
'''
