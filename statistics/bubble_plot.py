import plotly.express as px
import numpy as np

clients = []
matchings = []
blocks = []
gas = []

stats = open('stats_1.dat', 'r')
first = stats.readline()
for line in stats:
    clientNum, startBlock, matchingsNum, endBlock, gasTotal  = line.split()
    clients += [int(clientNum)]
    matchings += [int(matchingsNum)]
    # +1 since results phase has duration 0 in the experiment
    blocks += [str(int(endBlock) - int(startBlock) + 1)]
    gas += [int(gasTotal)]
    print(clientNum, startBlock, matchingsNum, endBlock, gasTotal)
stats.close()

print(clients)
print(matchings)
print(blocks)
print(gas)

fig = px.scatter(
    x=matchings,
    y=clients,
    color=blocks,
    size=gas
)

fig.update_layout(
    font_size=20,
    xaxis=dict(
        title='Number of Matchings'
    ),
    yaxis=dict(
        title='Number of Clients'
    ),
    legend=dict(
        y=0.99,
        x=0.01,
        title_text="Number of Blocks"
    )
)

fig.show()
