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
from flask import Flask, render_template, redirect, url_for, request

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------

# Smart Contract
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
    sys.exit("Error: Couldn't connect to the blockchain via web3")

# contract interface
darkPool = w3.eth.contract(address=contractAddress, abi=abi)

# Client Database
# initialise
registered = []
# read from file
file_name = './data/registered.dat'
try:
    f=open(file_name, 'r')
    for r in f:
        registered.append(r[:-1])
    f.close()
except:
    # file doesn't exist create it
    f=open(file_name, 'x')
    f.close()

# ------------------------------------------------------------------------------
# Flask Backend
# ------------------------------------------------------------------------------

app = Flask(__name__)

@app.route('/')
def intro():
    return render_template('index.html')

@app.route('/admin/', methods=["POST", "GET"])
def admin():
    if request.method == "POST":
        action = request.form["action"]
        addr = request.form["addr"]

        if action == 'r':
            if not addr in registered:
                registered.append(addr)
        elif action == 'd':
            if addr in registered:
                registered.remove(addr)

        f=open(file_name, 'w')
        for r in registered:
            f.write(r+'\n')
        f.close()
    return render_template('adminMeta.html', contractAddress = contractAddress, contractABI = json.dumps(abi))

@app.route('/client/', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        addr = request.form["addr"]
        if addr in registered:
            index = registered.index(addr)
            return redirect(url_for("client", id=index))
        else:
            return render_template('login.html')
    elif request.method == "GET":
        return render_template('login.html')

@app.route('/client/<id>/')
def client(id):
    return render_template('clientMeta.html', contractAddress = contractAddress, contractABI = json.dumps(abi))

if __name__ == '__main__':
    app.run(debug=True)
