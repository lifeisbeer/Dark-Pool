import plotly.graph_objects as go
from math import ceil
import numpy as np

gasTotal = 0
clients = [100,200,300,400,500,600,700,800,900,1000]

# tps = 0 (ideal conditions)
run = [2, 4, 5, 6, 8, 10, 11, 13, 14, 16]
gasTotal += 1855320048
# tps = 1
run1 = [3, 5, 8, 10, 13, 15, 18, 20, 23, 25]
gas1 = [31303492, 64211576, 96134416, 123685949, 159538424, 189768995, 220823230, 254660678, 287213527, 316651176]
gasTotal += 2114048606
# tps = 2
run2 = [3, 6, 9, 11, 14, 17, 20, 22, 25, 28]
gas2 = [32024447, 63166535, 95472087, 126262002, 158523525, 189459224, 223222675, 252495075, 283034505, 316267036]
gasTotal += 2192241254
# tps = 3
run3 = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30]
gas3 = [31715540, 63431755, 93603694, 125761500, 159273264, 189328367, 223325036, 252422952, 285671334, 317783771]
gasTotal += 2220839356
# tps = 4
run4 = [4, 7, 10, 13, 16, 19, 21, 25, 28, 31]
gas4 = [31877403, 63843923, 95265745, 126423625, 157419030, 190077938, 219381056, 252158728, 286801083, 317856938]
gasTotal += 2267507612
# tps = 5
run5 = [4, 7, 10, 13, 16, 19, 22, 25, 28, 31]
gas5 = [31774742, 63122824, 95251154, 126439476, 158199535, 190136540, 221898689, 251068980, 284447619, 315751595]
gasTotal += 2270709297
# tps = max
runMax = [4, 8, 10, 13, 16, 19, 22, 26, 29, 32]
gasMax = [31715396, 61681010, 96649305, 126054832, 158361578, 189034567, 220602899, 253599822, 287773075, 317856890]
gasTotal += 2301336517

gas = np.mean(np.array([gas1, gas2, gas3, gas4, gas5, gasMax]), axis=0)

print(sum((sum(run), sum(run1), sum(run2),  sum(run3),  sum(run4),  sum(run5),  sum(runMax))))
print(gasTotal)
print(gasTotal/15000000)
print(gas)

fig = go.Figure()

# Add traces
fig.add_trace(go.Scatter(x=clients, y=runMax,
                    mode='lines+markers',
                    name='+max tps'))
fig.add_trace(go.Scatter(x=clients, y=run5,
                    mode='lines+markers',
                    name='+5 tps'))
fig.add_trace(go.Scatter(x=clients, y=run4,
                    mode='lines+markers',
                    name='+4 tps'))
fig.add_trace(go.Scatter(x=clients, y=run3,
                    mode='lines+markers',
                    name='+3 tps'))
fig.add_trace(go.Scatter(x=clients, y=run2,
                    mode='lines+markers',
                    name='+2 tps'))
fig.add_trace(go.Scatter(x=clients, y=run1,
                    mode='lines+markers',
                    name='+1 tps'))
fig.add_trace(go.Scatter(x=clients, y=run,
                    mode='lines+markers',
                    name='+0 tps'))

fig.update_layout(
    font_size=20,
    xaxis=dict(
        title='Number of Clients'
    ),
    yaxis=dict(
        title='Runtime'
    ),
    legend=dict(
        y=0.99,
        x=0.01
    )
)

fig.show()

fig2 = go.Figure()

fig2.add_trace(go.Scatter(x=clients, y=gas,
                    mode='lines+markers',
                    name='+max tps'))

fig2.update_layout(
    font_size=20,
    xaxis=dict(
        title='Number of Clients'
    ),
    yaxis=dict(
        title='Gas'
    ),
    legend=dict(
        y=0.99,
        x=0.01
    )
)

fig2.show()
