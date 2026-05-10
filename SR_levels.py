import numpy as np
import pandas as pd
import scipy.stats as stats   

class SR_Levels:

    def pivot_high(self, series, left, right):
        pivots = np.full(len(series), np.nan)
    
        for i in range(left, len(series) - right):
            if (
                series.iloc[i] > series.iloc[i-left:i].max() and
                series.iloc[i] > series.iloc[i+1:i+right+1].max()
            ):
                # Pine confirmation delay
                pivots[i + right] = series.iloc[i]
    
        return pd.Series(pivots, index=series.index)
    
    def pivot_low(self, series, left, right):
        pivots = np.full(len(series), np.nan)
    
        for i in range(left, len(series) - right):
            if (
                series.iloc[i] < series.iloc[i-left:i].min() and
                series.iloc[i] < series.iloc[i+1:i+right+1].min()
            ):
                # Pine confirmation delay
                pivots[i + right] = series.iloc[i]
    
        return pd.Series(pivots, index=series.index)
    
    def SR_Daily_levels (self, df, swingSizeL = 2, swingSizeR = 2):

        df = df.copy()

        df_1d = df.resample('1D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        
        df_1d.loc[:,'pivHi'] = self.pivot_high(df_1d['high'], swingSizeL, swingSizeR)
        df_1d.loc[:,'pivLo'] = self.pivot_low(df_1d['low'],  swingSizeL, swingSizeR)
        
        pivots = pd.concat([
            df_1d.loc[df_1d['pivHi'].notna(), ['pivHi']]
              .rename(columns={'pivHi': 'price'})
              .assign(type='HIGH'),
        
            df_1d.loc[df_1d['pivLo'].notna(), ['pivLo']]
              .rename(columns={'pivLo': 'price'})
              .assign(type='LOW')
        ]).sort_index()
        
        levels = pivots.tail(6)


        df['SR_Tradable_Long'] = pd.Series(index=df.index, dtype='string')
        df['SR_Tradable_Short'] = pd.Series(index=df.index, dtype='string')

        # vela actual
        last = df_1d.iloc[-1]

        current_open = last['open']
        current_high = last['high']
        current_low = last['low']

        for _, row in levels.iterrows():

            level = row['price']
            level_type = row['type']

            # ---------------------------------
            # Resistance touched -> SHORT bias
            # ---------------------------------
            if current_open < level:
                if current_high >= level:
                    df.loc[df.index[-1], 'SR_Tradable_Short'] = "SHORT"

            # ---------------------------------
            # Support touched -> LONG bias
            # ---------------------------------
            elif current_open > level:

                if current_low <= level:
                    df.loc[df.index[-1], 'SR_Tradable_Long'] = "LONG"

        return levels    
    
df = pd.read_csv("DAX_Real_Time_Signal_Data.csv", index_col="time", parse_dates=True).drop_duplicates(keep="last")

SR = SR_Levels()
levels =SR.SR_Daily_levels (df,2, 2)

#print(levels)



