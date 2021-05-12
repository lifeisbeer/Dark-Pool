from math import ceil

count = 0
clients = []
matchings = []
blocks = []
gas = []

stats = open('statistics/stats_1.dat', 'r')
first = stats.readline()
for line in stats:
    clientNum, startBlock, matchingsNum, endBlock, gasTotal  = line.split()
    clients += [int(clientNum)]
    matchings += [int(matchingsNum)]
    # +1 since results phase has duration 0 in the experiment
    blocks += [int(endBlock) - int(startBlock) + 1]
    gas += [int(gasTotal)]
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

# block time parameters
transitions = 5
tr = 223
rev = 93
cal1 = 153
cal2 = 98
reg = 428

for i in range(count):

    print("Number of clients:", clients[i])
    print("Number of matchings:", matchings[i])

    # gas costs
    base_cost = clients[i]*(sub_ord+rev_ord+del1)
    min_cost = f1 + base_cost + pub2 + (matchings[i]-1)*pub1 + (matchings[i]+1)*(del2-del1) 
    max_cost = f2 + base_cost + pub2*matchings[i] + 2*matchings[i]*(del2-del1)

    # runtime
    base_time = 1 + transitions + ceil(clients[i]/tr) + ceil(clients[i]/rev) + ceil(clients[i]/reg)
    min_time = base_time + ceil(matchings[i]/cal1)
    max_time = base_time + ceil(matchings[i]/cal2)

    print("Theoretical gas cost: ({},{}] million".format(min_cost/1000, max_cost/1000))
    print("Actual gas cost: {} million".format(gas[i]/1000000))
    print("Theoretical runtime: ({},{}]".format(min_time, max_time))
    print("Actual runtime:", blocks[i])
    print("------------------------------------------------------------------------------")
