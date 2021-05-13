from math import ceil
import sys

# num of clients as command line argument
clients = int(sys.argv[1])
matchings = int(sys.argv[2])

count = 0

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

# gas costs for operator
base_op = clients*del1
min_op = f1 + base_op + pub2 + (matchings-1)*pub1 + (matchings+1)*(del2-del1)
max_op = f2 + base_op + pub2*matchings + 2*matchings*(del2-del1)

# gas costs
base_cost = base_op + clients*(sub_ord+rev_ord)
min_cost = f1 + base_cost + pub2 + (matchings-1)*pub1 + (matchings+1)*(del2-del1)
max_cost = f2 + base_cost + pub2*matchings + 2*matchings*(del2-del1)

# runtime
base_time = 1 + transitions + ceil(clients/tr) + ceil(clients/rev) + ceil(clients/reg)
min_time = base_time + ceil(matchings/cal1)
max_time = base_time + ceil(matchings/cal2)

print("Theoretical gas cost: ({},{}] million".format(min_cost/1000, max_cost/1000))
print("Theoretical operator gas cost: ({},{}] million".format(min_op/1000, max_op/1000))
print("Theoretical runtime: ({},{}]".format(min_time, max_time))
