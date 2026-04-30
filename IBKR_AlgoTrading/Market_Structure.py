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
                    
        if H_idx < L_idx:
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

def detect_risk(df, RM: int):

    pivots_with_direction(df, 20, 20)
    
    n = len(df)

    Risk_Long_arr  = np.full(n, np.nan)
    ST_Long_arr    = np.full(n, np.nan)
    Risk_Short_arr = np.full(n, np.nan)
    ST_Short_arr   = np.full(n, np.nan)
    last_high_arr  = np.full(n, np.nan)
    last_low_arr   = np.full(n, np.nan)
    lowest_arr   = np.full(n, np.nan)
    highest_arr   = np.full(n, np.nan)

    
    for i in range(n):
        
        sub = df.iloc[:i+1]
        close = df["close"].iloc[i]

        highs = sub.loc[sub['H']]
        lows  = sub.loc[sub['L']]

        if highs.empty or lows.empty:
            continue

        idx_high = highs.index[-1]
        idx_low  = lows.index[-1]

        last_high = df.loc[idx_high, 'high']
        last_low  = df.loc[idx_low, 'low']

        last_high_arr[i] = last_high
        last_low_arr[i]  = last_low

        pos_high = df.index.get_loc(idx_high)
        lowest = df["low"].iloc[pos_high:i+1].min()

        pos_low = df.index.get_loc(idx_low)
        highest = df["high"].iloc[pos_low:i+1].max()


        if idx_high < idx_low:  # estructura bajista

            ST_Short = last_high + abs(last_high - last_low) * (RM / 100)
            ST_Long  = lowest - abs(last_high - lowest) * (RM / 100)

            # calcular riesgo
            Risk_Short = (ST_Short - close) / ST_Short * 100
            Risk_Long  = (close - ST_Long) / ST_Long * 100

        elif idx_high > idx_low:  # estructura alcista

            ST_Long  = last_low - abs(last_high - last_low) * (RM / 100)
            ST_Short = highest + abs(highest - last_low) * (RM / 100)

            # calcular riesgo
            Risk_Short = (ST_Short - close) / close * 100
            Risk_Long  = (close - ST_Long) / close * 100

        Risk_Long_arr[i]  = Risk_Long
        ST_Long_arr[i]    = ST_Long
        Risk_Short_arr[i] = Risk_Short
        ST_Short_arr[i]   = ST_Short
        lowest_arr[i] = lowest
        highest_arr[i] = highest

    df["Risk_Long"]  = Risk_Long_arr
    df["ST_Long"]    = ST_Long_arr
    df["Risk_Short"] = Risk_Short_arr
    df["ST_Short"]   = ST_Short_arr
    df["last_high"]  = last_high_arr
    df["last_low"]   = last_low_arr
    df["lowest"]   = lowest_arr
    df["highest"]   = highest_arr

    return df


def wpr(df, length=40):
    highest = df["high"].rolling(length).max()
    lowest = df["low"].rolling(length).min()
    wpr = -100 * (highest - df["close"]) / (highest - lowest)
    return wpr

def hlc4(df):
    return (df['high'] + df['low'] + 2 * df['close']) / 4

def ema(series, length=8):
    return series.ewm(span=length, adjust=False).mean()

def std(series, period):
    return series.rolling(period).std()

# =========================
# OABC and Trend
# =========================

def Trend(df, lenght_short:int, lenght_long:int):

    n=len(df)
    Trend_arr  = np.full(n, np.nan)
    ema_short = ema(df["close"], lenght_short)
    ema_long = ema(df["close"], lenght_long)
    distance = ema_short-ema_long
    slope = distance.diff()
    trend = np.where(slope > 0, 1, -1)
    for i in range(n):
        Trend_arr[i]=trend

    df["Trend"]=Trend_arr

    return df #pd.Series(trend, index=df.index, name="trend")

def Upwards_OABC(df):
    return(
        (df["close"] > df["last_swing_high"])
        & (df["cero"]<df["last_swing_low"])
        & (df["wpr"] > -50)
    )

def Downwards_OABC(df):
    return(
        (df["close"] < df["last_swing_high"])
        & (df["cero"]>df["last_swing_low"])
        & (df["wpr"] < -50)
    )


def zigzag_with_structure(df, length=2):
    highs = df['high'].values
    lows = df['low'].values

    zigzag = []
    direction = None

    for i in range(length, len(df) - length):

        window_high = highs[i-length:i+length+1]
        window_low = lows[i-length:i+length+1]

        pivoth = highs[i] if highs[i] == window_high.max() else None
        pivotl = lows[i] if lows[i] == window_low.min() else None

        new_dir = direction

        if pivotl is not None and pivoth is None:
            new_dir = 'pl'
        elif pivoth is not None and pivotl is None:
            new_dir = 'ph'

        if new_dir is None:
            continue

        if direction != new_dir:
            price = pivoth if new_dir == 'ph' else pivotl
            wpr_values = df["wpr"].values
            zigzag.append((i, price, new_dir,wpr_values[i]))

            if len(zigzag) >= 3:
                p0 = zigzag[-1][1]
                p1 = zigzag[-2][1]
                p2 = zigzag[-3][1]

                if new_dir == 'ph':
                    swing = abs(p0-p1)
                    label = 'HH' if p0 > p2 else 'LH'
                    
                else:
                    swing = abs(p0-p1)
                    label = 'LL' if p0 < p2 else 'HL'
                    

                zigzag[-1] = (*zigzag[-1], label, swing)
            else:
                zigzag[-1] = (*zigzag[-1], None)

        else:
            if zigzag:
                last_idx, last_price, swing, last_dir,  wpr_at_pivot, *rest = zigzag[-1]

                if new_dir == 'ph' and pivoth is not None and pivoth > last_price:
                    zigzag[-1] = (i, pivoth, new_dir, wpr_values[i], rest[0] if rest else None)

                elif new_dir == 'pl' and pivotl is not None and pivotl < last_price:
                    zigzag[-1] = (i, pivotl, new_dir, wpr_values[i], rest[0] if rest else None)

        direction = new_dir

    return pd.DataFrame(zigzag, columns=['idx', 'price', 'dir',  'wpr', 'label', 'swing'])


def add_pivots_to_df(df, zz, zz_lf):

    df = df.copy()

    df["pivot_price"] = np.nan
    df["pivot_LF"] = np.nan
    #df["pivot_wpr"] = np.nan
    df["pivot_label"] = ""
    df["pivot_dir"] = ""
    df["pivot_high"] = np.nan
    df["pivot_low"] = np.nan

    df["dir_LF"] = np.nan

    for _, row in zz.iterrows():

        i = int(row["idx"])
        idx = df.index[i] 

        df.at[idx, "pivot_price"] = row["price"]
        #df.at[idx, "pivot_wpr"] = row["wpr"]
        df.at[idx, "pivot_label"] = str(row["label"]) if row["label"] is not None else ""
        df.at[idx, "pivot_dir"] = str(row["dir"])

        if row["dir"] == "ph":
            df.at[idx, "pivot_high"] = row["price"]

        elif row["dir"] == "pl":
            df.at[idx, "pivot_low"] = row["price"]


    idx_map = df.index[zz["idx"].astype(int)]

    df.loc[idx_map, "pivot_dir"] = zz["dir"].astype(str).values

    # Direction mapping
    dir_map = {"ph": -1, "pl": 1}
    df.loc[idx_map, "dir"] = zz["dir"].map(dir_map).values
    df["dir"] = df["dir"].ffill()

    # ---- Low-frequency direction (zz_lf) ----

    for _, row in zz_lf.iterrows():

        i = int(row["idx"])
        idx = df.index[i] 

        df.at[idx, "swing_LF"] = row["swing"]
        #df.at[idx, "pivot_wpr"] = row["wpr"]
        #df.at[idx, "pivot_label"] = str(row["label"]) if row["label"] is not None else ""
        #df.at[idx, "pivot_dir"] = str(row["dir"])

        if row["dir"] == "ph":
            df.at[idx, "high_LF"] = row["price"]

        elif row["dir"] == "pl":
            df.at[idx, "low_LF"] = row["price"]
            
    idx_map_lf = df.index[zz_lf["idx"].astype(int)]

    df.loc[idx_map_lf, "pivot_dir_LF"] = zz_lf["dir"].astype(str).values

    # Direction mapping
    dir_map = {"ph": -1, "pl": 1}
    df.loc[idx_map_lf, "dir_LF"] = zz_lf["dir"].map(dir_map).values
    df["dir_LF"] = df["dir_LF"].ffill()

    return df

def add_bos(df, buffer):

    n = len(df)

    bos_up_arr = np.full(n, False)
    bos_down_arr = np.full(n, False)

    last_high = None
    last_low = None
    wpr_high = None
    wpr_low = None

    for i in range(n):

        # actualizar pivots
        if not np.isnan(df['pivot_high'].iloc[i]):
            last_high = df['pivot_high'].iloc[i]
            wpr_high = df['wpr'].iloc[i]

        if not np.isnan(df['pivot_low'].iloc[i]):
            last_low = df['pivot_low'].iloc[i]
            wpr_low = df['wpr'].iloc[i]

        if last_high is None or last_low is None:
            continue

        close = df["close"].iloc[i]
        wpr   = df["wpr"].iloc[i]
        direction = df["dir_LF"].iloc[i]

        # --- BOS UP ---
        bos_up = (
            (direction == 1) and
            (wpr_low is not None and wpr_low > -50) and
            (close > last_high + buffer) and
            (wpr > -50)
        )

        # --- BOS DOWN ---
        bos_down = (
            (direction == -1) and
            (wpr_high is not None and wpr_high < -50) and
            (close < last_low - buffer) and
            (wpr < -50)
        )

        bos_up_arr[i] = bos_up
        bos_down_arr[i] = bos_down

    df["BOS_UP"] = bos_up_arr
    df["BOS_DOWN"] = bos_down_arr

    df["BOS_UP"] = df["BOS_UP"] & (~df["BOS_UP"].shift(1).fillna(False))
    df["BOS_DOWN"] = df["BOS_DOWN"] & (~df["BOS_DOWN"].shift(1).fillna(False))

    return df

def add_risk(df, RM: int):

    n = len(df)

    Risk_Long_arr  = np.full(n, np.nan)
    ST_Long_arr    = np.full(n, np.nan)
    Risk_Short_arr = np.full(n, np.nan)
    ST_Short_arr   = np.full(n, np.nan)
    last_high_arr  = np.full(n, np.nan)
    last_low_arr   = np.full(n, np.nan)
    lowest_arr     = np.full(n, np.nan)
    highest_arr    = np.full(n, np.nan)
    Distance_Long_arr     = np.full(n, np.nan)
    Distance_Short_arr    = np.full(n, np.nan)

    last_high_idx = None
    last_low_idx  = None

    for i in range(n):

        sub_high = df['high_LF'].iloc[:i+1]
        sub_low  = df['low_LF'].iloc[:i+1]

        last_high_LF_idx = sub_high.last_valid_index()
        last_low_LF_idx  = sub_low.last_valid_index()

        if last_high_LF_idx is None or last_low_LF_idx is None:
            continue

        last_high = df['high'].loc[last_high_LF_idx]
        last_low  = df['low'].loc[last_low_LF_idx]

        last_high_arr[i] = last_high
        last_low_arr[i]  = last_low

        pos_high = df.index.get_loc(last_high_LF_idx)
        pos_low  = df.index.get_loc(last_low_LF_idx)

        lowest = df['low'].iloc[pos_high:i+1].min()
        highest = df['high'].iloc[pos_low:i+1].max()

        close = df['close'].iloc[i]

        if df["dir_LF"].iloc[i] == -1:  # bearish Low-frequency 
            ST_Short = last_high + abs(last_high - last_low) * (RM / 100)
            ST_Long  = lowest - abs(last_high - lowest) * (RM / 100)

            Distance_Short =  abs(last_high - close)
            Distance_Long  = abs(close - lowest)            

        else:  # bullish Low-frequency
            ST_Long  = last_low - abs(last_high - last_low) * (RM / 100)
            ST_Short = highest + abs(highest - last_low) * (RM / 100)

            Distance_Long  = abs(close - last_low)
            Distance_Short = abs(highest - close)

        # unified risk formula (recommended)
        Risk_Short = (ST_Short - close) / close * 100
        Risk_Long  = (close - ST_Long) / close * 100

        Risk_Long_arr[i]  = Risk_Long
        ST_Long_arr[i]    = ST_Long
        Distance_Long_arr[i] = Distance_Long
        Risk_Short_arr[i] = Risk_Short
        ST_Short_arr[i]   = ST_Short
        Distance_Short_arr[i] = Distance_Short
        lowest_arr[i]     = lowest
        highest_arr[i]    = highest

    df["Risk_Long"]  = Risk_Long_arr
    df["ST_Long"]    = ST_Long_arr
    df["Distance_Long"] = Distance_Long_arr
    df["Risk_Short"] = Risk_Short_arr
    df["ST_Short"]   = ST_Short_arr
    df["Distance_Short"] = Distance_Short_arr
    #df["last_high"]  = last_high_arr
    #df["last_low"]   = last_low_arr
    #df["lowest"]     = lowest_arr
    #df["highest"]    = highest_arr

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
