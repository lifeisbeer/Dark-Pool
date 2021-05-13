import plotly.graph_objects as go
import numpy as np

z1 = np.zeros((100,100))
z2 = np.zeros((100,100))

for i in range(0, 100):
    for j in range(0, 100):
        z2[i,j] = 200000 + 35000*i + 152000*j
        z1[i,j] = 200000 + 35000*i + 98000*j

fig1 = go.Figure(data = go.Heatmap(
                            z=z1,
                            zmin=0,
                            zmax=np.amax(z2),
                            zsmooth='best',
                            x=list(range(100)),
                            y=list(range(100)),
                            colorbar=dict(
                                title='Gas Cost',
                                titleside='right',
                                titlefont=dict(
                                    size=14,
                                    family='Arial, sans-serif'
                                )
                            )
                        ),
                  layout = go.Layout(
                                width=600,
                                height=600
                                )
)

fig1.update_layout(
    xaxis_title="number of matchings (m_1)",
    yaxis_title="number of clients",
)

fig1.show()

fig2 = go.Figure(data = go.Heatmap(
                            z=z2,
                            zsmooth='best',
                            x=list(range(100)),
                            y=list(range(100)),
                            colorbar=dict(
                                title='Gas Cost',
                                titleside='right',
                                titlefont=dict(
                                    size=14,
                                    family='Arial, sans-serif'
                                )
                            )
                        ),
                  layout = go.Layout(
                                width=600,
                                height=600
                                )
)

fig2.update_layout(
    xaxis_title="number of matchings (m_2)",
    yaxis_title="number of clients"
)

fig2.show()
