from math import ceil
import sys

num = sys.argv[1]
gasSum = 1000*39000 + 86908796 + 3362347
count = 0
clients = []
matchings = []
blocks = []
ideal = []
gas = []

stats = open('stats_2_{}.dat'.format(num), 'r')
first = stats.readline()
for line in stats:
    clientNum, startBlock, matchingsNum, endBlock, gasTotal, actualBlocks = line.split()
    clients += [int(clientNum)]
    matchings += [int(matchingsNum)]
    blocks += [int(endBlock) - int(startBlock)]
    gas += [int(gasTotal)]
    ideal += [int(actualBlocks)]
    count += 1
stats.close()

# gas cost parameters
f1 = 165
f2 = 210
pub1 = 98
pub2 = 153
del1 = 35
del2 = 39
sub_ord = 67
rev_ord = 163

run = []
run2 = []

for i in range(count):

    print("Number of clients:", clients[i])
    print("Number of matchings:", matchings[i])

    # gas costs
    base_cost = clients[i]*(sub_ord+rev_ord+del1)
    min_cost = f1 + base_cost + pub2 + (matchings[i]-1)*pub1 + (matchings[i]+1)*(del2-del1)
    max_cost = f2 + base_cost + pub2*matchings[i] + 2*matchings[i]*(del2-del1)

    print("Theoretical gas cost: ({},{}] million".format(min_cost/1000, max_cost/1000))
    print("Actual gas cost: {} million".format(gas[i]/1000000))
    gasSum += gas[i]
    gasSum += 21000*(blocks[i]-ideal[i])

    run += [ceil(ideal[i]/230)]
    print("Theoretical runtime:", ceil(ideal[i]/230))
    run2 += [ceil(blocks[i]/230)]
    print("Actual runtime:", ceil(blocks[i]/230))
    print("------------------------------------------------------------------------------")

print(gasSum)
print(gas)
print(run2)
