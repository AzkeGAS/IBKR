import pandas as pd
import numpy as np

df_new = pd.read_csv("data.csv")
df_new["date"] = pd.to_datetime(df_new["date"])
df_historic["date"] = pd.to_datetime(df_historic["date"])

df = (
    pd.concat([df_historic, df_new])
      .drop_duplicates(subset=["id", "date"], keep="last")
      .sort_values("date")
      .reset_index(drop=True)
)

class SR_Levels()
    def __init__(self):
        self.pivots_subset = np.nan
        self.df.loc[:,tradable_long]=False
        self.df.loc[:,tradable_short]=False
        
    def pivot_high(series, left, right):
        pivots = np.full(len(series), np.nan)
    
        for i in range(left, len(series) - right):
            if (
                series.iloc[i] > series.iloc[i-left:i].max() and
                series.iloc[i] > series.iloc[i+1:i+right+1].max()
            ):
                # Pine confirmation delay
                pivots[i + right] = series.iloc[i]
    
        return pd.Series(pivots, index=series.index)
    
    def pivot_low(series, left, right):
        pivots = np.full(len(series), np.nan)
    
        for i in range(left, len(series) - right):
            if (
                series.iloc[i] < series.iloc[i-left:i].min() and
                series.iloc[i] < series.iloc[i+1:i+right+1].min()
            ):
                # Pine confirmation delay
                pivots[i + right] = series.iloc[i]
    
        return pd.Series(pivots, index=series.index)
    
    def SR_Daily_levels (df, swingSizeL = 2, swingSizeL = 2)
    
        df_1d = df.resample('1D', label='right', closed='right').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        
        df_1d['pivHi'] = pivot_high(df_1d['high'], swingSizeL, swingSizeR)
        df_1d['pivLo'] = pivot_low(df_1d['low'],  swingSizeL, swingSizeR)
        
        pivots = pd.concat([
            df_1d.loc[df_1d['pivHi'].notna(), ['pivHi']]
              .rename(columns={'pivHi': 'price'})
              .assign(type='HIGH'),
        
            df_1d.loc[df_1d['pivLo'].notna(), ['pivLo']]
              .rename(columns={'pivLo': 'price'})
              .assign(type='LOW')
        ]).sort_index()
        
        last_SR = pivots.tail(6)
        
        return last_SR

    def Tradable(df, df_1d, last_SR)
        if df_1d['open']<last_SR and df['low']<last_SR
            df[tradable_long] = True
        if df_1d['open']>last_SR and df['high']>last_SR
            df[tradable_short] = True
        if new df_1d candlestick
            df[tradable_long] = False
            df[tradable_short] = False
        
        
