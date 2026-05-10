import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import config
import threading
from SR_levels import *


global df_live

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("📈 Master Indicator Dashboard"),

    dcc.Graph(id='live-chart'),

    dcc.Interval(
        id='interval-component',
        interval=180000,  # every 5000 miliseconds
        n_intervals=0
    )
])


@app.callback(
    Output('live-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)

def update_chart(n):

    try:
        df = pd.read_csv("DAX_Back_Test_Data.csv", index_col="time", parse_dates=True).tail(2480) 
        # df = pd.read_csv("DAX_Real_Time_Signal_Data.csv", index_col="time", parse_dates=True).tail(480)

    
    except:
        return go.Figure()
    
    if df is None or df.empty or len(df) < 50:
        return go.Figure()
    
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    #levels = SR_Levels.SR_Daily_levels(df,2,2)


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
    
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['UpperBand'], 
        mode='lines', 
        name='UpperBand', 
        line=dict(
            color='green',   
            width=1,          
            dash='dashdot'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))
    
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['LowerBand'], 
        mode='lines', 
        name='LowerBand', 
        line=dict(
            color='green',   
            width=1,          
            dash='dashdot'      # style: 'solid', 'dot', 'dash', 'dashdot'
        )))


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
    
    # Zigzag Structure - connect H_tf and L_tf chronologically
    h_pivots = df[df['H_tf'].notna()][['H_tf']].reset_index()
    l_pivots = df[df['L_tf'].notna()][['L_tf']].reset_index()
    
    zigzag_points = []
    
    # Combine H_tf and L_tf with their indices
    for _, row in h_pivots.iterrows():
        zigzag_points.append((row['time'], row['H_tf']))
    for _, row in l_pivots.iterrows():
        zigzag_points.append((row['time'], row['L_tf']))
    
    # Sort by time to get chronological order
    zigzag_points.sort(key=lambda x: x[0])
    
    if zigzag_points:
        zigzag_x = [p[0] for p in zigzag_points]
        zigzag_y = [p[1] for p in zigzag_points]
        
        fig.add_trace(go.Scatter(
            x=zigzag_x,
            y=zigzag_y,
            mode='lines+markers',
            name='Zigzag Structure',
            line=dict(
                color='cyan',
                width=1,
                dash='solid'
            ),
            marker=dict(
                size=1,
                color='cyan',
                symbol='diamond'
            ),
            hovertemplate='<b>Pivot</b><br>%{x}<br>%{y:.2f}<extra></extra>'
        ))
    
    # Zigzag Structure - connect H and L chronologically (high frequency)
    h_pivots_hf = df[df['H'].notna()][['H']].reset_index()
    l_pivots_hf = df[df['L'].notna()][['L']].reset_index()
    
    zigzag_points_hf = []
    
    # Combine H and L with their indices
    for _, row in h_pivots_hf.iterrows():
        zigzag_points_hf.append((row['time'], row['H']))
    for _, row in l_pivots_hf.iterrows():
        zigzag_points_hf.append((row['time'], row['L']))
    
    # Sort by time to get chronological order
    zigzag_points_hf.sort(key=lambda x: x[0])
    
    if zigzag_points_hf:
        zigzag_x_hf = [p[0] for p in zigzag_points_hf]
        zigzag_y_hf = [p[1] for p in zigzag_points_hf]
        
        fig.add_trace(go.Scatter(
            x=zigzag_x_hf,
            y=zigzag_y_hf,
            mode='lines+markers',
            name='Zigzag Structure HF',
            line=dict(
                color='white',
                width=1,
                dash='dash'
            ),
            marker=dict(
                size=1,
                color='white',
                symbol='circle'
            ),
            hovertemplate='<b>HF Pivot</b><br>%{x}<br>%{y:.2f}<extra></extra>'
        ))
    
    Buy = df[(df["signal"] == "LONG")]

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

    Sell = df[(df["signal"] == "SHORT")]

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

    for _, row in levels.iterrows():

        color = "green" if row['type'] == "HIGH" else "red"

        fig.add_hline(
            y=row['price'],
            line_dash="dash",
            line_color=color
        )

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