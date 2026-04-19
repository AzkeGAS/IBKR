import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import config
import threading
from Market_Structure import *
import data_store

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

    # === ADX ===
    df["adx"] = adx(df, 7, 7)

    # === Valores previos ===
    df["sig_prev"] = df["adx"].shift(1)
    df["wpr_prev"] = df["wpr"].shift(1)

    wpr = df["wpr"]
    sig = df["adx"]
    wpr_prev = df["wpr_prev"]
    sig_prev = df["sig_prev"]

    # === Condiciones vectorizadas ===
    conditions = [
        (wpr < -72) & (sig >= sig_prev) & (wpr < wpr_prev),
        (wpr < -50) & (wpr > -72) & (sig >= sig_prev) & (wpr < wpr_prev),
        (wpr < -50) & (sig <= sig_prev) & (wpr < wpr_prev),
        (wpr > -50) & (sig <= sig_prev) & (wpr > wpr_prev),
        (wpr > -50) & (sig >= sig_prev) & (wpr < wpr_prev),
        (wpr > -27) & (sig >= sig_prev) & (wpr > wpr_prev),
        (wpr > -50) & (wpr < -27) & (sig >= sig_prev) & (wpr > wpr_prev),
        (wpr < -50) & (sig >= sig_prev) & (wpr > wpr_prev),
        (wpr < -50),
        (wpr > -50)
    ]

    choices = [
        "dark_brown",
        "orange_brown",
        "orange",
        "yellow",
        "red",
        "dark_green",
        "light_green",
        "green",
        "fuchsia",
        "navy"
    ]

    # === Resultado final ===
    df["color"] = np.select(conditions, choices, default="gray")
    df["color_plotly"] = df["color"].map({
        "dark_brown": "rgb(100,40,50)",
        "orange_brown": "rgb(210,60,130)",
        "orange": "rgb(250,140,0)",
        "yellow": "rgb(255,250,0)",
        "red": "rgb(255,0,0)",
        "dark_green": "rgb(70,100,70)",
        "light_green": "rgb(120,185,70)",
        "green": "rgb(0,255,0)",
        "fuchsia": "rgb(255,0,255)",
        "navy": "rgb(0,0,150)",
        "gray": "gray"
    })

    # Altura del cuerpo
    df["body"] = df["close"] - df["open"]

    # Base del cuerpo
    df["base"] = df["open"]

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
   
    fig.add_trace(go.Bar(
        x=df.index,
        y=df["body"],
        base=df["base"],
        marker=dict(color=df["color_plotly"]),
        width=5,
        showlegend=False
    ))

    # ZigZag from pivots
    for i in range(len(zz) - 1):
        p1 = zz.iloc[i]
        p2 = zz.iloc[i+1]

        fig.add_trace(go.Scatter(
            x=[df.iloc[p1['idx']].name, df.iloc[p2['idx']].name],
            y=[p1['price'], p2['price']],
            mode='lines',
            name='1h ZigZag',
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


        fig.add_trace(go.Scatter(x=df.index, 
            y=df['UpperBand'], 
            mode='lines', 
            name='UpperBand', 
            line=dict(
                color='blue',   
                width=1,          
                dash='dash'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))


        fig.add_trace(go.Scatter(x=df.index,
            y=df['LowerBand'], 
            mode='lines', 
            name='LowerBand', 
            line=dict(
                color='red',   
                width=1,          
                dash='dash'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))


        fig.add_trace(go.Scatter(x=df.index,
            y=df['ST_Long'], 
            mode='lines', 
            name='ST_Long', 
            line=dict(
                color='red',      
                width=1,          
                dash='solid'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))


        fig.add_trace(go.Scatter(x=df.index,
            y=df['ST_Short'], 
            mode='lines', 
            name='ST_Short', 
            line=dict(
                color='blue',   
                width=1,         
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

#---------candle color-------------------
def rma(series, length):
    return series.ewm(alpha=1/length, adjust=False).mean()

def dirov(df, length):
    up = df["high"].diff()
    down = -df["low"].diff()

    plusDM = np.where((up > down) & (up > 0), up, 0.0)
    minusDM = np.where((down > up) & (down > 0), down, 0.0)

    tr = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift(1)),
            abs(df["low"] - df["close"].shift(1))
        )
    )

    tr_rma = rma(pd.Series(tr), length)
    plus_rma = rma(pd.Series(plusDM), length)
    minus_rma = rma(pd.Series(minusDM), length)

    plus = 100 * (plus_rma / tr_rma).fillna(0)
    minus = 100 * (minus_rma / tr_rma).fillna(0)

    return plus, minus

def adx(df, di_len=7, adx_len=7):
    plus, minus = dirov(df, di_len)

    sum_dm = plus + minus
    dx = 100 * (abs(plus - minus) / sum_dm.replace(0, 1))

    adx_val = rma(dx, adx_len)

    return adx_val

def get_bar_color(wpr, sig, wpr_prev, sig_prev):

    if wpr < -72 and sig >= sig_prev and wpr < wpr_prev:
        return "dark_brown"

    elif wpr < -50 and wpr > -72 and sig >= sig_prev and wpr < wpr_prev:
        return "orange_brown"

    elif wpr < -50 and sig <= sig_prev and wpr < wpr_prev:
        return "orange"

    elif wpr > -50 and sig <= sig_prev and wpr > wpr_prev:
        return "yellow"

    elif wpr > -50 and sig >= sig_prev and wpr < wpr_prev:
        return "red"

    elif wpr > -27 and sig >= sig_prev and wpr > wpr_prev:
        return "dark_green"

    elif wpr > -50 and wpr < -27 and sig >= sig_prev and wpr > wpr_prev:
        return "light_green"

    elif wpr < -50 and sig >= sig_prev and wpr > wpr_prev:
        return "green"

    elif wpr < -50:
        return "fuchsia"

    elif wpr > -50:
        return "navy"

    else:
        return "gray"


