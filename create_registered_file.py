import sys
from web3 import Web3, HTTPProvider

# command line arguments
if len(sys.argv) == 2:
    client_num = int(sys.argv[1])
else:
    sys.exit("Error! Include client number as argument.")

# setup web3 instance using ganache
ganache_url = "http://127.0.0.1:8545"
w3 = Web3(HTTPProvider(ganache_url))
if w3.isConnected():
    print("Web3 Connected")
else:
    sys.exit("Error: Couldn't connect to the blockchain via web3.")

file_name = './data/registered.dat'
f=open(file_name, 'w')
for i in range(1, client_num+1):
    f.write(w3.eth.accounts[i]+'\n')
f.close()

print("Wrote {} addresses to file {}.".format(client_num, file_name))
