from web3 import Web3, HTTPProvider
import sys
import os
import time
import random

# ------------------------------------------------------------------------------
# Parameters
# ------------------------------------------------------------------------------

def_gas = 50000000000
# values used:          1, 0.5, 0.25, 0.125, 0.0625, 0   seconds
# which correspond to: +1,  +2,   +3,    +4,     +5, max tps
transaction_delay = 0.25
client = int(sys.argv[1])

min = round(0.5*def_gas)
max = round(1.5*def_gas)

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------

# setup web3 instance using ganache
ganache_url = "http://127.0.0.1:8545"
w3 = Web3(HTTPProvider(ganache_url))
if w3.isConnected():
    print("Web3 Connected")
else:
    sys.exit("Error: Couldn't connect to the blockchain via web3")

# ------------------------------------------------------------------------------
# Generate Transactions
# ------------------------------------------------------------------------------

while True:

    # generate random number to simulate different gas prices
    #gas = round(random.triangular(min, max, def_gas))

    # send 1 wei
    w3.eth.sendTransaction({
        "from" : w3.eth.accounts[client],
        "to" : w3.eth.accounts[client-1],
        'value': w3.toWei(1, 'wei'),
        'gasPrice': w3.toWei(def_gas, 'wei'),
    })

    # wait some time before sendig the next transaction
    time.sleep(transaction_delay)
