import os
import json
from web3 import Web3, HTTPProvider
import sys
import binascii

# path to parent directory
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# contract path
contract_path = parent_path+'/truffle/build/contracts/darkPool.json'

# open compiled file and get abi & bytecode
truffleFile = json.load(open(contract_path))
abi = truffleFile['abi']
bytecode = truffleFile['bytecode']

# setup web3 instance using testnet
f=open('./data/endpoint.dat', 'r')
testnet_endpoint = f.read()
f.close()
w3 = Web3(HTTPProvider(testnet_endpoint))
if w3.isConnected():
    print("Web3 Connected")
else:
    sys.exit("Error: Couldn't connect to the blockchain via web3")

# instanciate contract
contract = w3.eth.contract(abi=abi, bytecode=bytecode)

# get owner account using private key
f=open('./data/key_owner.dat', 'r')
key = f.read()
f.close()
accnt = w3.eth.account.privateKeyToAccount(key)

# build transaction
build_tx = contract.constructor().buildTransaction({
    'from': accnt.address,
    'nonce': w3.eth.getTransactionCount(accnt.address),
    'gas': 6721975, # from truffle docs
    'gasPrice': 100000000000 # from truffle docs
})
# sign transaction
sign_tx = accnt.signTransaction(build_tx)
# send transaction
tx_hash = w3.eth.sendRawTransaction(sign_tx.rawTransaction)
# wait for transaction to be mined
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=300)
print("Contract deployed at address: {}".format(tx_receipt.contractAddress))

# save address to file
f=open('./data/address.dat', 'w')
f.write(tx_receipt.contractAddress)
f.close()
