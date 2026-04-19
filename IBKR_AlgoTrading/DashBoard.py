import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import config
import threading
from Market_Structure import *


global df_live

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("📈 Master Indicator V04 Dashboard"),

    dcc.Graph(id='live-chart'),

    dcc.Interval(
        id='interval-component',
        interval=5000,  # every 5000 miliseconds
        n_intervals=0
    )
])

@app.callback(
    Output('live-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)

def update_chart(n):

    try:
        df = pd.read_csv("Market_structure.csv", index_col="time", parse_dates=True) 
    
    except:
        return go.Figure()
    
    if df is None or df.empty or len(df) < 50:
        return go.Figure()
    
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)

    df = main_indicator(df)
    #df_3m= pivots_with_direction(df_3m, left=1, right=1)
    #df_3m = mtf_pivots_with_direction(df_3m, left=40, right=40)
    #df_3m = detect_bos(df=df_3m,buffer= config.buffer)
            
    zz = zigzag_with_structure(df,1)
    zz = zz[zz['dir'] != zz['dir'].shift()]
    zz1= zigzag_with_structure(df,40)
    zz1 = zz1[zz1['dir'] != zz1['dir'].shift()]

    df = add_pivots_to_df(df,zz, zz1)
    df = add_risk(df, config.RB)
    df = add_bos(df, config.buffer)
    

    fig = go.Figure()

    # Price Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="Price",
        increasing=dict(line=dict(color='green'), fillcolor='green'),
        decreasing=dict(line=dict(color='red'), fillcolor='red'),
    ))
   
    # Indicators

    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['EMA155'], 
        mode='lines', 
        name='EMA155', 
        line=dict(
            color='green',   
            width=1,          
            dash='solid'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))
    
    # ZigZag from pivots
    for i in range(len(zz) - 1):
        p1 = zz.iloc[i]
        p2 = zz.iloc[i+1]

        fig.add_trace(go.Scatter(
            x=[df.iloc[p1['idx']].name, df.iloc[p2['idx']].name],
            y=[p1['price'], p2['price']],
            mode='lines',
            name='3min ZigZag',
            line=dict(
                color='white',
                width=1,
                dash='dot'
            ),
            showlegend=False
        ))


    # ZigZag from pivots
    for i in range(len(zz1) - 1):
        p1 = zz1.iloc[i]
        p2 = zz1.iloc[i+1]

        fig.add_trace(go.Scatter(
            x=[df.index[p1['idx']], df.index[p2['idx']]],
            y=[p1['price'], p2['price']],
            mode='lines',
            name='1h ZigZag',
            line=dict(
                color='white',
                width=2,
                dash='dash'
            ),
            showlegend=False
        ))

    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['ST_Long'], 
        mode='lines', 
        name='ST_Long', 
        line=dict(
            color='red',   
            width = 1,          
            dash='solid'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))
    
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['ST_Short'], 
        mode='lines', 
        name='ST_Short', 
        line=dict(
            color='blue',   
            width = 1,          
            dash='solid'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))
    
    Buy = df[(df["BOS_UP"] == True) & (~df["BOS_UP"].shift(1).fillna(False))]

    if not Buy.empty:
        fig.add_trace(go.Scatter(
            x=Buy.index,
            y=Buy["ST_Long"],
            mode="markers",
            name="Buy",
            marker=dict(
                color="green",
                size=10,
                symbol="triangle-up",
                line=dict(width=1, color="black")
            )
        ))

    Sell = df[(df["BOS_DOWN"] == True) & (~df["BOS_DOWN"].shift(1).fillna(False))]

    if not Sell.empty:
        fig.add_trace(go.Scatter(
            x=Sell.index,
            y=Sell["ST_Short"],
            mode="markers",
            name="Sell",
            marker=dict(
                color="red",
                size=10,
                symbol="triangle-down",
                line=dict(width=1, color="black")
            )
        ))

    fig.update_layout(
        template='plotly_dark',

        # Chart behavior
        hovermode='x unified',
        dragmode='pan',

        # Remove range slider
        xaxis_rangeslider_visible=False,

        # Margins (important for tight layout)
        margin=dict(l=10, r=10, t=30, b=10),

        # Legend styling
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),

        # Background colors
        paper_bgcolor='black',
        plot_bgcolor='black',

        # Font
        font=dict(size=10),

        bargap=0
    )
    fig.update_traces(
        hoverinfo="x+y"
    )
    fig.update_xaxes(rangeslider_visible=False)
    fig.update_xaxes(type="date")
    fig.update_xaxes(
    rangebreaks=[
        dict(bounds=["sat", "mon"]),
        dict(bounds=[23, 2])
    ]
)

    return fig

app.run(debug=True)