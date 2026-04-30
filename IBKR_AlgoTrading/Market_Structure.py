import numpy as np
import pandas as pd


# =========================
# MODULES
# =========================


import pandas as pd

def main_indicator(df):
    #EMA
    df['EMA8']=ema(hlc4(df),8)
    df['EMA155']=ema(hlc4(df),155)
    
    # Bands with multiplier 2
    df['UpperBand'] = df['EMA155'] + 2 * std(hlc4(df),155)
    df['LowerBand'] = df['EMA155'] - 2 * std(hlc4(df),155)
    
    df["wpr"]=wpr(df,40)

    return df

def HFMS(df, left=1, right=1): # High frequency ZigZag and BOS check
    highs = df['high'].values
    lows = df['low'].values
    close = df['close'].iloc[-1]

    df['dir'] = np.nan    # 1 = up, -1 = down
    df["H"] = np.nan        # pivot high
    df["L"] =np.nan        # pivot low
    df["BOS"] =np.nan        # pivot low
    
    for i in range(left, len(df) - right):

        window_high = highs[i-left:i+right+1]
        window_low  = lows[i-left:i+right+1]

        is_pivot_high = highs[i] == window_high.max()
        is_pivot_low  = lows[i]  == window_low.min()

        if is_pivot_high:
            df.at[i, 'H'] = highs[i]
            H_idx = i
            
        elif is_pivot_low:
            df.at[i, 'L'] = lows[i]
            L_idx = i
                    
        if H_idx < L_idx:
            df.at[i,'dir'] = 1
            p0 = df.at[i, 'close']
            p1 = df["L"].dropna().iloc[-1]
            p2 = df["H"].dropna().iloc[-1]
            wpr0 = df.at[i, 'wpr']
            wpr1 = df.at[L_idx, 'wpr']
            wpr2 = df.at[H_idx, 'wpr']
            
            if p0>=(p2+buffer) & wpr0>=-50 & wpr2>=-50
                df.at[i,'BOS']= "UP"
            elif p0>=(p2+buffer) & wpr0>=-50 & wpr1>=-50
                df.at[i,'BOS']="UP"
            
        else
            df.at[i,'dir'] = -1
            p0 = df.at[i, 'close']
            p1 = df["H"].dropna().iloc[-1]
            p2 = df["L"].dropna().iloc[-1]
            wpr0 = df.at[i, 'wpr']
            wpr1 = df.at[H_idx, 'wpr']
            wpr2 = df.at[L_idx, 'wpr']

            if p0<=(p2-buffer) & wpr0<=-50 & wpr2<=-50
                df.at[i,'BOS']="DOWN"
            elif p0<=(p2-buffer) & wpr0<=-50 & wpr1<=-50
                df.at[i,'BOS']="DOWN"
    return df

def TFMS(df, left=20, right=20):    #Low frequency ZigZag and Risk assessment
    highs = df['high'].values
    lows = df['low'].values
    close = df['close'].iloc[-1]

    df['dir_tf'] = np.nan    # 1 = up, -1 = down
    df["H_tf"] = np.nan        # pivot high
    df["L_tf"] =np.nan        # pivot low
    df['swing_tf'] = np.nan  # last swing length
    
    df["Risk_Long"]  =  np.nan  # Risk long
    df["ST_Long"]    =  np.nan  # Stop Loss Long
    df["Risk_Short"] =  np.nan  # Risk short
    df["ST_Short"]   =  np.nan  # Stop Loss Short
    
    for i in range(left, len(df) - right):

        window_high = highs[i-left:i+right+1]
        window_low  = lows[i-left:i+right+1]

        is_pivot_high = highs[i] == window_high.max()
        is_pivot_low  = lows[i]  == window_low.min()

        if is_pivot_high:
            df.at[i, 'H_tf'] = highs[i]
            H_idx = i
            
        elif is_pivot_low:
            df.at[i, 'L_tf'] = lows[i]
            L_idx = i
                    
        if H_idx > L_idx:
            df.at[i,'dir_tf'] = -1
            p0 = df.loc[H_idx:, 'low'].min()
            p1 = df["H_tf"].dropna().iloc[-1]
            p2 = df["L_tf"].dropna().iloc[-1]
            df.at[i,'swing_tf'] = p2-p1
            wpr_tf = df.at[i, 'wpr']
            
            df.at[i,'ST_Short'] = p1 + abs(p1 - p2) * (RM / 100)
            df.at[i,'ST_Long']  = p0 - abs(p1 - p0) * (RM / 100)

            # calcular riesgo
            df.at[i,'Risk_Short'] = (ST_Short - close) / ST_Short * 100
            df.at[i,'Risk_Long']  = (close - ST_Long) / ST_Long * 100
            
        else
            df.at[i,'dir'] = 1
            p0 = df.loc[L_idx:, 'high'].max()
            p1 = df["H_tf"].dropna().iloc[-1]
            p2 = df["L_tf"].dropna().iloc[-1]
            df.at[i,'swing_tf'] = p1-p2
            wpr_tf = df.at[i, 'wpr']

            df.at[i,'ST_Long'] = p1 + abs(p1 - p2) * (RM / 100)
            df.at[i,'ST_Short']  = p0 - abs(p1 - p0) * (RM / 100)

            # calcular riesgo
            df.at[i,'Risk_Short'] = (ST_Short - close) / ST_Short * 100
            df.at[i,'Risk_Long']  = (close - ST_Long) / ST_Long * 100

    return df

def Low_frequency_range(df):
    import pandas as pd

    df = df.copy()

    # Asegurar datetime
    df.index = pd.to_datetime(df.index)
    
    serie = df['swing_LF'].replace("", pd.NA).dropna()
    serie_pct = serie / df['close'].iloc[-1]*100

    # Seguridad: necesita al menos 2 valores
    if len(serie) < 2:
        return {
            "mean_range": pd.NA,
            "median_range": pd.NA,
            "std_range": pd.NA,
            "max_range": pd.NA,
            "min_range": pd.NA,
            "mean_range_pct": pd.NA,
            "std_range_pct": pd.NA
        }

    stats = {
        "mean_range": serie.mean(),
        "median_range": serie.median(),
        "std_range": serie.std(),
        "max_range": serie.max(),
        "min_range": serie.min(),
        "mean_range_pct": serie_pct.mean(),
        "std_range_pct": serie_pct.std()
    }

    return stats
