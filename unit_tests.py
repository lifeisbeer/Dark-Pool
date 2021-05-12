import json
from web3 import Web3, HTTPProvider
import sys
from ecies.utils import generate_eth_key, generate_key
from ecies import encrypt, decrypt
import random
import hashlib
from operator import itemgetter

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------

# contract details
contract_path = './truffle/build/contracts/darkPool.json'

# open compiled file and get abi & bytecode
truffleFile = json.load(open(contract_path))
abi = truffleFile['abi']
bytecode = truffleFile['bytecode']

# setup web3 instance using ganache
ganache_url = "http://127.0.0.1:8545"
w3 = Web3(HTTPProvider(ganache_url))
if w3.isConnected():
    print("Web3 Connected")
else:
    sys.exit("Couldn't connect to the blockchain via web3")
# set default account
w3.eth.defaultAccount = w3.eth.accounts[0]

# instanciate contract
DarkPool = w3.eth.contract(abi=abi, bytecode=bytecode)
# deploy contract (call constructor)
tx_hash = DarkPool.constructor().transact()
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
print("Contract deployed at address: {} and block: {}"
      .format(tx_receipt.contractAddress, w3.eth.blockNumber))
contractAddress = tx_receipt.contractAddress

# contract interface
darkPool = w3.eth.contract(address=contractAddress, abi=abi)

# create a filter to be notified when we are in a new phase
# this event contains 2 fields: 'currentState' and 'expirationTime'
phase_filter = darkPool.events.startPhase.createFilter(fromBlock="latest")
# create a filter to be notified when a commitment is revealed
# this event contains 3 fields: 'sender', 'commitment' and 'ciphertext'
order_filter = darkPool.events.commitmentRevealed.createFilter(fromBlock="latest")
# create a filter to be notified when a secret key is revealed
# this event contains 4 fields: 'sender', 'commitment', 'ciphertext' and 'secret'
secret_filter = darkPool.events.secretRevealed.createFilter(fromBlock="latest")
# create a filter to be notified when a matching is published
# this event contains 5 fields: 'buyer', 'seller', 'asset', 'amount' and 'price'
match_filter = darkPool.events.logTrade.createFilter(fromBlock="latest")

# ------------------------------------------------------------------------------
# Unit Tests
# ------------------------------------------------------------------------------

test_num = 1
# IMPORTANT: ganache needs to have at least clients+4 accounts!!!
# IMPORTANT: we need at least 2 clients in order to test matches!!!
clients = 2

'''
-> index for key participants:
operator:                                                       0,
not_reg:                                                        1,
clients:                                    [ 2, ..., clients+1 ],
registered, commits, doesn't reveal:                    clients+2,
registered, doesn't commit, doesnn't reveal:             clints+3
'''

# ----- Initialisation Tests: -----

# check the initialisation of the contract variables
assert darkPool.functions.phase().call() == 0, "Test {} failed: Phase not initialised correctly.".format(test_num)
test_num += 1
assert darkPool.functions.operator().call() == w3.eth.accounts[0], "Test 2 failed: Operator not initialised correctly.".format(test_num)
test_num += 1
for i in range(2, clients+4):
    # get address
    addr = w3.eth.accounts[i]
    assert darkPool.functions.us_pk(addr).call() == b'', "Test {} failed: Public-key not initialised correctly.".format(test_num)
    test_num += 1
    assert darkPool.functions.orders(addr).call()[0] == b'', "Test {} failed: Commitment not initialised correctly.".format(test_num)
    test_num += 1
    assert darkPool.functions.orders(addr).call()[1] == b'', "Test {} failed: Ciphertext not initialised correctly.".format(test_num)
    test_num += 1
    assert darkPool.functions.orders(addr).call()[2] == b'', "Test {} failed: Secret-key not initialised correctly.".format(test_num)
    test_num += 1

phase_tests = test_num - 1
print("Initialisation tests passed     ({:3d} tests)".format(phase_tests))


# ----- Constrains Tests: -----

# non-operator tries to register client
try:
    tx_hash = darkPool.functions.register_client(w3.eth.accounts[2], b'1').transact({'from':w3.eth.accounts[1]})
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Non-Operator can register clients.".format(test_num))
# non-operator tries to remove order
try:
    tx_hash = darkPool.functions.register_client(w3.eth.accounts[2], b'1').transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    tx_hash = darkPool.functions.remove_order(w3.eth.accounts[2]).transact({'from':w3.eth.accounts[1]})
except:
    tx_hash = darkPool.functions.remove_order(w3.eth.accounts[2]).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    test_num += 1
else:
    raise Exception("Test {} failed: Non-Operator can remove orders.".format(test_num))
# non-operator tries to remove client
try:
    tx_hash = darkPool.functions.register_client(w3.eth.accounts[2], b'1').transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    tx_hash = darkPool.functions.remove_client(w3.eth.accounts[2]).transact({'from':w3.eth.accounts[1]})
except:
    tx_hash = darkPool.functions.remove_client(w3.eth.accounts[2]).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    test_num += 1
else:
    raise Exception("Test {} failed: Non-Operator can remove clients.".format(test_num))
# non-operator tries to change to trading phase
try:
    tx_hash = darkPool.functions.trading_phase(0,0).transact({'from':w3.eth.accounts[1]})
except:
    test_num += 1
    tx_hash = darkPool.functions.trading_phase(0,0).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
else:
    raise Exception("Test {} failed: Non-Operator can change phase.".format(test_num))
# non-operator tries to change to reveal phase
try:
    tx_hash = darkPool.functions.reveal_phase(0).transact({'from':w3.eth.accounts[1]})
except:
    test_num += 1
    tx_hash = darkPool.functions.reveal_phase(0).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
else:
    raise Exception("Test {} failed: Non-Operator can change phase.".format(test_num))
# non-operator tries to change to calculation phase
try:
    tx_hash = darkPool.functions.calc_phase().transact({'from':w3.eth.accounts[1]})
except:
    test_num += 1
    tx_hash = darkPool.functions.calc_phase().transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
else:
    raise Exception("Test {} failed: Non-Operator can change phase.".format(test_num))
# non-operator tries to change to results phase
try:
    tx_hash = darkPool.functions.res_phase(0).transact({'from':w3.eth.accounts[1]})
except:
    test_num += 1
    tx_hash = darkPool.functions.res_phase(0).transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
else:
    raise Exception("Test {} failed: Non-Operator can change phase.".format(test_num))
# non-operator tries to change to registration phase
try:
    tx_hash = darkPool.functions.reg_phase().transact({'from':w3.eth.accounts[1]})
except:
    test_num += 1
    tx_hash = darkPool.functions.reg_phase().transact()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
else:
    raise Exception("Test {} failed: Non-Operator can change phase.".format(test_num))
event = phase_filter.get_new_entries()

phase_tests = test_num - phase_tests - 1
print("Constrains tests passed         ({:3d} tests)".format(phase_tests))
phase_tests = test_num - 1


# ----- Registration Phase Tests: -----

addr2keys = {}
for i in range(2, clients+4):
    # get address
    addr = w3.eth.accounts[i]
    # generate key pair
    addr2keys[addr] = generate_key()
    pk = addr2keys[addr].public_key.format(True)

    # register client
    tx_hash = darkPool.functions.register_client(addr, pk).transact()
    # wait for the transaction to be mined
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    assert darkPool.functions.us_pk(addr).call() == pk, "Test {} failed: Public-key not assigned correctly.".format(test_num)
    test_num += 1

    # remove client
    tx_hash = darkPool.functions.remove_client(addr).transact()
    # wait for the transaction to be mined
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    #print("Remove client gas used:", tx_receipt.gasUsed)
    assert darkPool.functions.us_pk(addr).call() == b'', "Test {} failed: Public-key not deleted.".format(test_num)
    test_num += 1

    # try to remove client again
    try:
        tx_hash = darkPool.functions.remove_client(addr).transact()
    except:
        test_num += 1
    else:
        raise Exception("Test {} failed: Same client can be removed multiple times.".format(test_num))

    # register client again
    tx_hash = darkPool.functions.register_client(addr, pk).transact()
    # wait for the transaction to be mined
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    assert darkPool.functions.us_pk(addr).call() == pk, "Test {} failed: Public-key not assigned correctly.".format(test_num)
    test_num += 1

# check that no public key was assigned to a non-registered client
assert darkPool.functions.us_pk(w3.eth.accounts[1]).call() == b'', "Test {} failed: Public key should be empty.".format(test_num)
test_num += 1

#check that we can't call functions that need a different phase
# reveal_match -> Cal
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[0], b'1', 'b', w3.eth.accounts[1], b'2', 's', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_match can be called at the wrong phase.".format(test_num))
# commit_order -> Trd
try:
    tx_hash = darkPool.functions.commit_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: commit_order can be called at the wrong phase.".format(test_num))
# cancel_order -> Trd
try:
    tx_hash = darkPool.functions.cancel_order().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: cancel_order can be called at the wrong phase.".format(test_num))
# change_order -> Trd
try:
    tx_hash = darkPool.functions.change_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: change_order can be called at the wrong phase.".format(test_num))
# reveal_order -> Rev
try:
    tx_hash = darkPool.functions.reveal_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_order can be called at the wrong phase.".format(test_num))

# ckeck that we can't go to a different phase
# operator tries to chnage to reveal phase
try:
    tx_hash = darkPool.functions.reveal_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to calculation phase
try:
    tx_hash = darkPool.functions.calc_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to results phase
try:
    tx_hash = darkPool.functions.res_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to registration phase
try:
    tx_hash = darkPool.functions.reg_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))

phase_tests = test_num - phase_tests - 1
print("Registration Phase tests passed ({:3d} tests)".format(phase_tests))
phase_tests = test_num - 1


# ----- Trading Phase Tests: -----

# try to pass an invalid auction mode
try:
    tx_hash = darkPool.functions.trading_phase(1,123).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can declare invalid auction matching mode.".format(test_num))

# change phase
tx_hash = darkPool.functions.trading_phase(1,1).transact()
# wait for the transaction to be mined
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
assert darkPool.functions.phase().call() == 1, "Test {} failed: Trading Phase not initialised correctly.".format(test_num)
test_num += 1
# check auction mode
assert darkPool.functions.auctionMode().call() == 1, "Test {} failed: Auction mode not initialised correctly.".format(test_num)
test_num += 1

# get phase event
event = phase_filter.get_new_entries()
# only 1 phase event should have been emitted
assert len(event) == 1, "Test {} failed: Contract should emit only 1 phase event.".format(test_num)
test_num += 1
# check that phase and expiration on event are correct
phase = event[0]['args']['currentState']
assert phase == 1, "Test {} failed: Reported phase is incorrect".format(test_num)
test_num += 1
expiration = event[0]['args']['expirationTime']
assert expiration == w3.eth.blockNumber+1, "Test {} failed: Reported expiration is incorrect".format(test_num)
test_num += 1
# no other event type (order, secret, match) should be emitted
event = order_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Order event emitted incorrectly.".format(test_num)
test_num += 1
event = secret_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Secret event emitted incorrectly.".format(test_num)
test_num += 1
event = match_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Match event emitted incorrectly.".format(test_num)
test_num += 1

# clients send their commitments
ciphertexts = {}
for i in range(2, clients+3):
    addr = w3.eth.accounts[i]

    # make a commitment
    order_string = "{},{},{},{},{},{}".format('b','a',i,10+i,20+i,111*i)
    # encode order string
    order_bytes = order_string.encode('utf-8')
    # encrypt order bytes
    ciphertext = encrypt(addr2keys[addr].public_key.format(True), order_bytes)
    # hash ciphertext
    hash = hashlib.sha3_256(ciphertext).digest()
    # send commitment to contract
    tx_hash = darkPool.functions.commit_order(hash).transact({'from':addr})
    # wait for transaction receipt
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    #print("Commit gas used:", tx_receipt.gasUsed)
    # check if the commitment text on the contract matches the one send
    assert darkPool.functions.orders(addr).call()[0] == hash, "Test {} failed: Commitment received is incorrect.".format(test_num)
    test_num += 1

    # try to commit again (not change but commit twice)
    try:
        tx_hash = darkPool.functions.commit_order(b'1').transact({'from':addr})
    except:
        test_num += 1
    else:
        raise Exception("Test {} failed: Client can commit multiple times.".format(test_num))

    # make a different commitment and change the one on the contract
    order_string = "{},{},{},{},{},{}".format('s','b',i+1,11+i,21+i,222*i)
    # encode order string
    order_bytes = order_string.encode('utf-8')
    # encrypt order bytes
    ciphertext = encrypt(addr2keys[addr].public_key.format(True), order_bytes)
    # store ciphertext for later
    ciphertexts[addr] = ciphertext
    # hash ciphertext
    hash = hashlib.sha3_256(ciphertext).digest()
    # send commitment to contract
    tx_hash = darkPool.functions.change_order(hash).transact({'from':addr})
    # wait for transaction receipt
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    #print("Change commitment gas used:", tx_receipt.gasUsed)
    # check if the commitment text on the contract matches the one send
    assert darkPool.functions.orders(addr).call()[0] == hash, "Test {} failed: Commitment received is incorrect.".format(test_num)
    test_num += 1

    # cancel the commitment
    tx_hash = darkPool.functions.cancel_order().transact({'from':addr})
    # wait for transaction receipt
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    #print("Cancel commitment gas used:", tx_receipt.gasUsed)
    # check if the commitment text on the contract matches the one send
    assert darkPool.functions.orders(addr).call()[0] == b'', "Test {} failed: Commitment was not deleted.".format(test_num)
    test_num += 1

    # try to cancel again
    try:
        tx_hash = darkPool.functions.cancel_order().transact({'from':addr})
    except:
        test_num += 1
    else:
        raise Exception("Test {} failed: Client can cancel multiple times.".format(test_num))

    # try to change while not commited
    try:
        tx_hash = darkPool.functions.change_order(b'1').transact({'from':addr})
    except:
        test_num += 1
    else:
        raise Exception("Test {} failed: Client can change order without commiting.".format(test_num))

    # make the previous commitment again
    tx_hash = darkPool.functions.commit_order(hash).transact({'from':addr})
    # wait for transaction receipt
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    # check if the commitment text on the contract matches the one send
    assert darkPool.functions.orders(addr).call()[0] == hash, "Test {} failed: Commitment received is incorrect.".format(test_num)
    test_num += 1

# check that the commitment is empty for a client who didn't send commitmnet
assert darkPool.functions.orders(w3.eth.accounts[1]).call()[0] == b'', "Test {} failed: Commitment should be empty.".format(test_num)
test_num += 1

# not registered tries to commit order
try:
    tx_hash = darkPool.functions.commit_order(b'1').transact(w3.eth.accounts[1])
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Not registered client can commit order.".format(test_num))
# not registered tries to cancel order
try:
    tx_hash = darkPool.functions.cancel_order().transact(w3.eth.accounts[1])
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Not registered client can cancel order.".format(test_num))
# not registered tries to change order
try:
    tx_hash = darkPool.functions.change_order(b'1').transact(w3.eth.accounts[1])
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Not registered client can change order.".format(test_num))

#check that we can't call functions that need a different phase
# register_client -> Reg
try:
    tx_hash = darkPool.functions.register_client(w3.eth.accounts[1], b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: register_client can be called at the wrong phase.".format(test_num))
# remove_order -> Reg
try:
    tx_hash = darkPool.functions.remove_order(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_order can be called at the wrong phase.".format(test_num))
# remove_client -> Reg
try:
    tx_hash = darkPool.functions.remove_client(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_client can be called at the wrong phase.".format(test_num))
# reveal_match -> Cal
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[0], b'1', 'b', w3.eth.accounts[1], b'2', 's', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_match can be called at the wrong phase.".format(test_num))
# reveal_order -> Rev
try:
    tx_hash = darkPool.functions.reveal_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_order can be called at the wrong phase.".format(test_num))

# ckeck that we can't go to a different phase
# operator tries to chnage trading to phase
try:
    tx_hash = darkPool.functions.trading_phase(0,0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to calculation phase
try:
    tx_hash = darkPool.functions.calc_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to results phase
try:
    tx_hash = darkPool.functions.res_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to registration phase
try:
    tx_hash = darkPool.functions.reg_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))

phase_tests = test_num - phase_tests - 1
print("Trading Phase tests passed      ({:3d} tests)".format(phase_tests))
phase_tests = test_num - 1


# ----- Reveal Phase Tests: -----

# change phase
tx_hash = darkPool.functions.reveal_phase(1).transact()
# wait for the transaction to be mined
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
assert darkPool.functions.phase().call() == 2, "Test {} failed: Reveal Phase not initialised correctly.".format(test_num)
test_num += 1

# get phase event
event = phase_filter.get_new_entries()
# only 1 phase event should have been emitted
assert len(event) == 1, "Test {} failed: Contract should emit only 1 phase event.".format(test_num)
test_num += 1
# check that phase and expiration on event are correct
phase = event[0]['args']['currentState']
assert phase == 2, "Test {} failed: Reported phase is incorrect".format(test_num)
test_num += 1
expiration = event[0]['args']['expirationTime']
assert expiration == w3.eth.blockNumber+1, "Test {} failed: Reported expiration is incorrect".format(test_num)
test_num += 1
# no other event type (order, secret, match) should be emitted
event = order_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Order event emitted incorrectly.".format(test_num)
test_num += 1
event = secret_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Secret event emitted incorrectly.".format(test_num)
test_num += 1
event = match_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Match event emitted incorrectly.".format(test_num)
test_num += 1

# client reveal orders
for i in range(2, clients+2):
    addr = w3.eth.accounts[i]
    ciphertext = ciphertexts[addr]
    # send ciphertext
    tx_hash = darkPool.functions.reveal_order(ciphertext).transact({'from':addr})
    # wait for the transaction to be mined
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    # check if the ciphertext on the contract matches the one send
    assert darkPool.functions.orders(addr).call()[1] == ciphertext, "Test {} failed: Ciphertext received is incorrect.".format(test_num)
    test_num += 1

    # try to reveal again
    try:
        tx_hash = darkPool.functions.reveal_order(b'1').transact({'from':addr})
    except:
        test_num += 1
    else:
        raise Exception("Test {} failed: Client can reveal multiple times.".format(test_num))

    # check if order event was emitted
    event = order_filter.get_new_entries()
    assert len(event) == 1, "Test {} failed: Contract should emit 1 Order event after every revealed order.".format(test_num)
    test_num += 1
    # check that sender, commitment and ciphertext on event are correct
    sender = event[0]['args']['sender']
    assert sender == addr, "Test {} failed: Reported sender is incorrect".format(test_num)
    test_num += 1
    commitment = event[0]['args']['commitment']
    assert commitment == hashlib.sha3_256(ciphertext).digest(), "Test {} failed: Reported commitment is incorrect".format(test_num)
    test_num += 1
    recCiphertext = event[0]['args']['ciphertext']
    assert recCiphertext == ciphertext, "Test {} failed: Reported ciphertext is incorrect".format(test_num)
    test_num += 1

# check that the ciphertext is empty for a client who didn't send ciphertext
assert darkPool.functions.orders(w3.eth.accounts[1]).call()[1] == b'', "Test {} failed: Ciphertext should be empty.".format(test_num)
test_num += 1

# not registered tries to reveal order
try:
    tx_hash = darkPool.functions.reveal_order(b'1').transact(w3.eth.accounts[1])
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Not registered client can reveal order.".format(test_num))
# registered client that didn't commit tries to reveal order
try:
    tx_hash = darkPool.functions.reveal_order(b'1').transact(w3.eth.accounts[clients+3])
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Not commited client can reveal order.".format(test_num))

#check that we can't call functions that need a different phase
# register_client -> Reg
try:
    tx_hash = darkPool.functions.register_client(w3.eth.accounts[1], b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: register_client can be called at the wrong phase.".format(test_num))
# remove_order -> Reg
try:
    tx_hash = darkPool.functions.remove_order(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_order can be called at the wrong phase.".format(test_num))
# remove_client -> Reg
try:
    tx_hash = darkPool.functions.remove_client(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_client can be called at the wrong phase.".format(test_num))
# reveal_match -> Cal
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[0], b'1', 'b', w3.eth.accounts[1], b'2', 's', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_match can be called at the wrong phase.".format(test_num))
# commit_order -> Trd
try:
    tx_hash = darkPool.functions.commit_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: commit_order can be called at the wrong phase.".format(test_num))
# cancel_order -> Trd
try:
    tx_hash = darkPool.functions.cancel_order().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: cancel_order can be called at the wrong phase.".format(test_num))
# change_order -> Trd
try:
    tx_hash = darkPool.functions.change_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: change_order can be called at the wrong phase.".format(test_num))

# ckeck that we can't go to a different phase
# operator tries to chnage trading to phase
try:
    tx_hash = darkPool.functions.trading_phase(0,0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to reveal phase
try:
    tx_hash = darkPool.functions.reveal_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to results phase
try:
    tx_hash = darkPool.functions.res_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to registration phase
try:
    tx_hash = darkPool.functions.reg_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))

phase_tests = test_num - phase_tests - 1
print("Reveal Phase tests passed       ({:3d} tests)".format(phase_tests))
phase_tests = test_num - 1


# ----- Calculation Phase Tests: -----

# change phase
tx_hash = darkPool.functions.calc_phase().transact()
# wait for the transaction to be mined
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
assert darkPool.functions.phase().call() == 3, "Test {} failed: Calculation Phase not initialised correctly.".format(test_num)
test_num += 1

# get phase event
event = phase_filter.get_new_entries()
# only 1 phase event should have been emitted
assert len(event) == 1, "Test {} failed: Contract should emit only 1 phase event.".format(test_num)
test_num += 1
# check that phase and expiration on event are correct
phase = event[0]['args']['currentState']
assert phase == 3, "Test {} failed: Reported phase is incorrect".format(test_num)
test_num += 1
expiration = event[0]['args']['expirationTime']
assert expiration == 0, "Test {} failed: Reported expiration is incorrect".format(test_num)
test_num += 1
# no other event type (order, secret, match) should be emitted
event = order_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Order event emitted incorrectly.".format(test_num)
test_num += 1
event = secret_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Secret event emitted incorrectly.".format(test_num)
test_num += 1
event = match_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Match event emitted incorrectly.".format(test_num)
test_num += 1

# read commitments and ciphertext for each client
for i in range(2, clients+2):
    # get address
    addr = w3.eth.accounts[i]
    # get order from contract
    order = darkPool.functions.orders(addr).call()
    commitment = order[0]
    ciphertext = order[1]
    # check if ciphertext matches commitment
    assert commitment == hashlib.sha3_256(ciphertext).digest(), "Test {} failed: Received commitment doesn't match with received ciphertext.".format(test_num)
    test_num += 1

# try seller == buyer
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[2], b'1', '1', w3.eth.accounts[2], b'2', '2', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Seller=Buyer in revealed match.".format(test_num))
# try seller who didn't reveal
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[2], b'1', '1', w3.eth.accounts[clients+2], b'2', '2', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Seller in match didn't reveal.".format(test_num))
# try buyer who didn't reveal
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[clients+2], b'1', '1', w3.eth.accounts[2], b'2', '2', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Buyer in match didn't reveal.".format(test_num))
# try seller who didn't commit
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[2], b'1', '1', w3.eth.accounts[clients+3], b'2', '2', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Seller in match didn't commit.".format(test_num))
# try buyer who didn't commit
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[clients+3], b'1', '1', w3.eth.accounts[2], b'2', '2', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Buyer in match didn't commit.".format(test_num))

for i in range(2, clients+1):
    b = w3.eth.accounts[i]
    bSK = addr2keys[b].secret
    s = w3.eth.accounts[i+1]
    sSK = addr2keys[s].secret
    # operator publishes matched orders
    tx_hash = darkPool.functions.reveal_match('a', b, bSK, str(i), s, sSK, str(i+1), 10*i, 100*i).transact()
    # wait for the transaction to be mined
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    # check if the secret keys are published correctly
    assert darkPool.functions.orders(b).call()[2] == bSK, "Test {} failed: Buyer secret key received is incorrect.".format(test_num)
    test_num += 1
    assert darkPool.functions.orders(s).call()[2] == sSK, "Test {} failed: Seller secret key received is incorrect.".format(test_num)
    test_num += 1

    # check if both secretRevealed events were emitted
    events = secret_filter.get_new_entries()
    assert len(events) == 2, "Test {} failed: Contract should emit 2 secretRevealed events.".format(test_num)
    test_num += 1
    for e in events:
        # check that client, commitment, ciphertext and secret key on event are correct
        sender = e['args']['sender']
        assert sender == b or sender == s, "Test {} failed: Reported sender is incorrect".format(test_num)
        test_num += 1
        commitment = e['args']['commitment']
        assert commitment == hashlib.sha3_256(ciphertexts[sender]).digest(), "Test {} failed: Reported commitment is incorrect".format(test_num)
        test_num += 1
        recCiphertext = e['args']['ciphertext']
        assert recCiphertext == ciphertexts[sender], "Test {} failed: Reported ciphertext is incorrect".format(test_num)
        test_num += 1
        secret = e['args']['secret']
        assert secret == bSK or secret == sSK, "Test {} failed: Reported secret key is incorrect".format(test_num)
        test_num += 1

    # check if logTrade event is emitted
    event = match_filter.get_new_entries()
    assert len(event) == 1, "Test {} failed: Contract should emit 1 logTrade event.".format(test_num)
    test_num += 1
    # check that bName, sName, asset, amount and price on event are correct
    buyer = event[0]['args']['buyer']
    assert buyer == str(i), "Test {} failed: Reported buyer is incorrect".format(test_num)
    test_num += 1
    seller = event[0]['args']['seller']
    assert seller == str(i+1), "Test {} failed: Reported seller is incorrect".format(test_num)
    test_num += 1
    asset = event[0]['args']['asset']
    assert asset == 'a', "Test {} failed: Reported asset is incorrect".format(test_num)
    test_num += 1
    amount = event[0]['args']['amount']
    assert amount == 10*i, "Test {} failed: Reported amount is incorrect".format(test_num)
    test_num += 1
    price = event[0]['args']['price']
    assert price == 100*i, "Test {} failed: Reported price is incorrect".format(test_num)
    test_num += 1

# check that the secret key is empty for a client who didn't participate
assert darkPool.functions.orders(w3.eth.accounts[1]).call()[2] == b'', "Test {} failed: Commitment should be empty.".format(test_num)
test_num += 1

#check that we can't call functions that need a different phase
# register_client -> Reg
try:
    tx_hash = darkPool.functions.register_client(w3.eth.accounts[1], b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: register_client can be called at the wrong phase.".format(test_num))
# remove_order -> Reg
try:
    tx_hash = darkPool.functions.remove_order(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_order can be called at the wrong phase.".format(test_num))
# remove_client -> Reg
try:
    tx_hash = darkPool.functions.remove_client(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_client can be called at the wrong phase.".format(test_num))
# commit_order -> Trd
try:
    tx_hash = darkPool.functions.commit_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: commit_order can be called at the wrong phase.".format(test_num))
# cancel_order -> Trd
try:
    tx_hash = darkPool.functions.cancel_order().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: cancel_order can be called at the wrong phase.".format(test_num))
# change_order -> Trd
try:
    tx_hash = darkPool.functions.change_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: change_order can be called at the wrong phase.".format(test_num))
# reveal_order -> Rev
try:
    tx_hash = darkPool.functions.reveal_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_order can be called at the wrong phase.".format(test_num))

# ckeck that we can't go to a different phase
# operator tries to chnage trading to phase
try:
    tx_hash = darkPool.functions.trading_phase(0,0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to reveal phase
try:
    tx_hash = darkPool.functions.reveal_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to calculation phase
try:
    tx_hash = darkPool.functions.calc_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to registration phase
try:
    tx_hash = darkPool.functions.reg_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))

phase_tests = test_num - phase_tests - 1
print("Calculation Phase tests passed  ({:3d} tests)".format(phase_tests))
phase_tests = test_num - 1


# ----- Results Phase Tests: -----

# change phase
tx_hash = darkPool.functions.res_phase(1).transact()
# wait for the transaction to be mined
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
assert darkPool.functions.phase().call() == 4, "Test {} failed: Results Phase not initialised correctly.".format(test_num)
test_num += 1

# get phase event
event = phase_filter.get_new_entries()
# only 1 phase event should have been emitted
assert len(event) == 1, "Test {} failed: Contract should emit only 1 phase event.".format(test_num)
test_num += 1
# check that phase and expiration on event are correct
phase = event[0]['args']['currentState']
assert phase == 4, "Test {} failed: Reported phase is incorrect".format(test_num)
test_num += 1
expiration = event[0]['args']['expirationTime']
assert expiration == w3.eth.blockNumber+1, "Test {} failed: Reported expiration is incorrect".format(test_num)
test_num += 1
# no other event type (order, secret, match) should be emitted
event = order_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Order event emitted incorrectly.".format(test_num)
test_num += 1
event = secret_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Secret event emitted incorrectly.".format(test_num)
test_num += 1
event = match_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Match event emitted incorrectly.".format(test_num)
test_num += 1

#check that we can't call functions that need a different phase
# register_client -> Reg
try:
    tx_hash = darkPool.functions.register_client(w3.eth.accounts[1], b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: register_client can be called at the wrong phase.".format(test_num))
# remove_order -> Reg
try:
    tx_hash = darkPool.functions.remove_order(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_order can be called at the wrong phase.".format(test_num))
# remove_client -> Reg
try:
    tx_hash = darkPool.functions.remove_client(w3.eth.accounts[1]).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: remove_client can be called at the wrong phase.".format(test_num))
# reveal_match -> Cal
try:
    tx_hash = darkPool.functions.reveal_match(w3.eth.accounts[0], b'1', 'b', w3.eth.accounts[1], b'2', 's', 1, 1).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_match can be called at the wrong phase.".format(test_num))
# commit_order -> Trd
try:
    tx_hash = darkPool.functions.commit_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: commit_order can be called at the wrong phase.".format(test_num))
# cancel_order -> Trd
try:
    tx_hash = darkPool.functions.cancel_order().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: cancel_order can be called at the wrong phase.".format(test_num))
# change_order -> Trd
try:
    tx_hash = darkPool.functions.change_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: change_order can be called at the wrong phase.".format(test_num))
# reveal_order -> Rev
try:
    tx_hash = darkPool.functions.reveal_order(b'1').transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: reveal_order can be called at the wrong phase.".format(test_num))

# ckeck that we can't go to a different phase
# operator tries to chnage trading to phase
try:
    tx_hash = darkPool.functions.trading_phase(0,0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to reveal phase
try:
    tx_hash = darkPool.functions.reveal_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to calculation phase
try:
    tx_hash = darkPool.functions.calc_phase().transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))
# operator tries to chnage to results phase
try:
    tx_hash = darkPool.functions.res_phase(0).transact()
except:
    test_num += 1
else:
    raise Exception("Test {} failed: Operator can change to the wrong phase.".format(test_num))

phase_tests = test_num - phase_tests - 1
print("Results Phase tests passed      ({:3d} tests)".format(phase_tests))
phase_tests = test_num - 1


# ----- Second Registration Phase Tests: -----

# change phase
tx_hash = darkPool.functions.reg_phase().transact()
# wait for the transaction to be mined
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
assert darkPool.functions.phase().call() == 0, "Test {} failed: Registration Phase not initialised correctly.".format(test_num)
test_num += 1

# get phase event
event = phase_filter.get_new_entries()
# only 1 phase event should have been emitted
assert len(event) == 1, "Test {} failed: Contract should emit only 1 phase event.".format(test_num)
test_num += 1
# check that phase and expiration on event are correct
phase = event[0]['args']['currentState']
assert phase == 0, "Test {} failed: Reported phase is incorrect".format(test_num)
test_num += 1
expiration = event[0]['args']['expirationTime']
assert expiration == 0, "Test {} failed: Reported expiration is incorrect".format(test_num)
test_num += 1
# no other event type (order, secret, match) should be emitted
event = order_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Order event emitted incorrectly.".format(test_num)
test_num += 1
event = secret_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Secret event emitted incorrectly.".format(test_num)
test_num += 1
event = match_filter.get_new_entries()
assert len(event) == 0, "Test {} failed: Match event emitted incorrectly.".format(test_num)
test_num += 1

# check that the contract variables are reset to empty
for i in range(2, clients+4):
    # get address
    addr = w3.eth.accounts[i]

    # remove order
    tx_hash = darkPool.functions.remove_order(addr).transact()
    # wait for the transaction to be mined
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    #print("Remove order gas used:", tx_receipt.gasUsed)
    assert darkPool.functions.orders(addr).call()[0] == b'', "Test {} failed: Commitment not reset correctly.".format(test_num)
    test_num += 1
    assert darkPool.functions.orders(addr).call()[1] == b'', "Test {} failed: Ciphertext not reset correctly.".format(test_num)
    test_num += 1
    assert darkPool.functions.orders(addr).call()[2] == b'', "Test {} failed: Secret-key not reset correctly.".format(test_num)
    test_num += 1

    # remove client
    tx_hash =  darkPool.functions.remove_client(addr).transact()
    # wait for the transaction to be mined
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    #print("Remove client gas used:", tx_receipt.gasUsed)
    assert darkPool.functions.us_pk(addr).call() == b'', "Test {} failed: Public-key not reset correctly.".format(test_num)
    test_num += 1

phase_tests = test_num - phase_tests - 1
print("Reset tests passed              ({:3d} tests)".format(phase_tests))
phase_tests = test_num - 1


print("All tests passed                ({:3d} tests)".format(test_num-1))
