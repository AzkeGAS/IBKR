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
        
        df['pivHi'] = pivot_high(df_1d['high'], swingSizeL, swingSizeR).shift(-swingSizeR)
        df['pivLo'] = pivot_low(df_1d['low'],  swingSizeL, swingSizeR).shift(-swingSizeR)
        
        pivots = pd.concat([
            df.loc[df['pivHi'].notna(), ['pivHi']]
              .rename(columns={'pivHi': 'price'})
              .assign(type='HIGH'),
        
            df.loc[df['pivLo'].notna(), ['pivLo']]
              .rename(columns={'pivLo': 'price'})
              .assign(type='LOW')
        ]).sort_index()
        
        self.pivots_subset = pivots.iloc[1:4]
        print(self.pivots_subset)
        
        return self.pivots_subset
