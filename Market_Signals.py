
import numpy as np
import pandas as pd
import scipy.stats as stats
from SR_levels import *

# =========================
# MODULES
# =========================
# 
class SignalEngine:

    def hlc4(self, df):
        return (df['high'] + df['low'] + 2 * df['close']) / 4

    def ema(self, series, length=8):
                return series.ewm(span=length, adjust=False).mean()

    def std(self, series, period):
                return series.rolling(period).std()
            
    def wpr(self, df, period):
        df = df.copy()
        highest_high = df['high'].rolling(period).max()
        lowest_low = df['low'].rolling(period).min()
        wpr = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
        return wpr
            
    def main_indicator(self, df):
    
        df = df.copy()
    
        # ---- HLC4 ----
        hlc4 = self.hlc4(df)
    
        # ---- EMA ----
        df['EMA8'] = self.ema(hlc4, 8)
        df['EMA155'] = self.ema(hlc4, 155)
    
        # ---- Bands (Bollinger-style on EMA155) ----
        std155 = self.std(hlc4, 155)
        df['UpperBand'] = df['EMA155'] + 2 * std155
        df['LowerBand'] = df['EMA155'] - 2 * std155
    
        # ---- Trend (EMA spread smoothed) ----
        ema123 = self.ema(hlc4, 123)
        ema188 = self.ema(hlc4, 188)
    
        trend_raw = ema123 - ema188
        df['Trend'] = self.ema(trend_raw, 2)
    
        # ---- Velocity & Acceleration (smoothed) ----
        velocity = df['Trend'].pct_change()
        velocity = self.ema(velocity, 2)
    
        df['Velocity'] = velocity
        df['Acceleration'] = velocity.diff()
    
        # ---- WPR ----
        df['WPR'] = self.wpr(df, 40)
    
        return df

    # =========================
    # High frequency ZigZag and BOS check
    # =========================

    def HFMS_vectorized(self, df, left=1, right=1):

        df = df.copy()
   
        # Step 1: pivots
        window = left + right + 1
        df.loc[:, 'H'] = np.where(
            df['high'] == df['high'].rolling(window, center=True).max(),
            df['high'], np.nan
        )
        df.loc[:, 'L'] = np.where(
            df['low'] == df['low'].rolling(window, center=True).min(),
            df['low'], np.nan
        )

        # backtest-safe
        #df.loc[:, 'H'] = df['H'].shift(right)
        #df.loc[:, 'L'] = df['L'].shift(right)

        # Step 2: pivot indices
        df.loc[:, 'H_idx'] = np.where(df['H'].notna(), np.arange(len(df)), np.nan)
        df.loc[:, 'L_idx'] = np.where(df['L'].notna(), np.arange(len(df)), np.nan)
        df.loc[:, 'H_idx'] = df['H_idx'].ffill()
        df.loc[:, 'L_idx'] = df['L_idx'].ffill()

        # Step 3: direction
        df.loc[:, 'dir'] = np.where(df['H_idx'] < df['L_idx'], 1,
        np.where(df['H_idx'] > df['L_idx'], -1, np.nan)
        )

        # Step 4: last pivot values
        df.loc[:, 'last_H'] = df['H'].ffill()
        df.loc[:, 'last_L'] = df['L'].ffill()

        return df

    def multi_timeframe_zigzag(self, df1, df2):
    
        # --- Copy to avoid modifying originals ---
        df1 = df1.copy()
        df2 = df2.copy()
    
        # --- Ensure datetime + sorting ---
        df1['time'] = pd.to_datetime(df1['time'])
        df2['time'] = pd.to_datetime(df2['time'])
    
        df1 = df1.sort_values('time').reset_index(drop=True)
        df2 = df2.sort_values('time').reset_index(drop=True)
    
        # --- Compute zigzag ---
        df1 = self.HFMS_vectorized(df1, left=1, right=1)
        df2 = self.HFMS_vectorized(df2, left=2, right=2)  # smoother HTF
    
        # --- Select + rename HTF columns ---
        cols_to_map = ['time', 'H', 'L', 'dir', 'last_H', 'last_L']
    
        df2_map = df2[cols_to_map].copy().rename(columns={
            'H': 'H_2',
            'L': 'L_2',
            'dir': 'dir_2',
            'last_H': 'last_H_2',
            'last_L': 'last_L_2'
        })
    
        # --- CRITICAL: sort both before merge_asof ---
        df1 = df1.sort_values('time')
        df2_map = df2_map.sort_values('time')
    
        # --- Merge HTF into LTF ---
        df = pd.merge_asof(
            df1,
            df2_map,
            on='time',
            direction='backward'
        )
    
        # --- Forward fill HTF structure ---
        htf_cols = ['H_2', 'L_2', 'dir_2', 'last_H_2', 'last_L_2']
        df[htf_cols] = df[htf_cols].ffill()
    
        return df

    def BOS_detection(df, buffer=3):

        df.loc[:, 'H_wpr'] = df['wpr'].where(df['H'].notna()).ffill()
        df.loc[:, 'L_wpr'] = df['wpr'].where(df['L'].notna()).ffill()

        # Step 5: BOS
        up = (
            (df['dir'] == 1) &
            (df['close'] >= df['last_H'] + buffer) &
            (df['wpr'] >= -50) &
            ((df['H_wpr'] >= -50) | (df['L_wpr'] >= -50) | (df['wpr_lf'] >= -50))
        )

        down = (
            (df['dir'] == -1) &
            (df['close'] <= df['last_L'] - buffer) &
            (df['wpr'] <= -50) &
            ((df['H_wpr'] <= -50) | (df['L_wpr'] <= -50) | (df['wpr_lf'] <= -50))
        )

        df.loc[:, 'BOS'] = np.where(up, 'UP', np.where(down, 'DOWN', np.nan))

        return df

    def SL_RA(self, df, RM=10):
    
        df = df.copy()
    
        # --------------------------------------------------
        # 1. Index tracking for HTF pivots
        # --------------------------------------------------
        idx = np.arange(len(df))
    
        df['H_idx_2'] = np.where(df['H_2'].notna(), idx, np.nan)
        df['L_idx_2'] = np.where(df['L_2'].notna(), idx, np.nan)
    
        df['H_idx_2'] = df['H_idx_2'].ffill()
        df['L_idx_2'] = df['L_idx_2'].ffill()
    
        # --------------------------------------------------
        # 2. Last pivots
        # --------------------------------------------------
        df['last_H_2'] = df['H_2'].ffill()
        df['last_L_2'] = df['L_2'].ffill()
    
        # --------------------------------------------------
        # 3. Extremes since pivot (✅ correct, no future leak)
        # --------------------------------------------------
        df['low_since_H_2'] = df['low'].groupby(df['H_idx_2']).cummin()
        df['high_since_L_2'] = df['high'].groupby(df['L_idx_2']).cummax()
    
        # --------------------------------------------------
        # 4. Swing
        # --------------------------------------------------
        df['swing_2'] = df['last_H_2'] - df['last_L_2']
    
        # ✅ FIX: 'filtered_type' was undefined → remove or replace
        df['swing_H_2'] = np.where(df['dir_2'] == -1, df['swing_2'], np.nan)
        df['swing_L_2'] = np.where(df['dir_2'] == 1, -df['swing_2'], np.nan)
    
        swing_up_mean = df['swing_H_2'].dropna().mean() / 2
        swing_down_mean = df['swing_L_2'].dropna().mean() / 2
    
        # --------------------------------------------------
        # 5. Stops
        # --------------------------------------------------
        rm = RM / 100
        close = df['close']
    
        long_mask = df['dir_2'] == 1
    
        df['ST_Long'] = np.where(
            long_mask,
            df['last_L_2'] - df['swing_2'].abs() * rm,
            df['low_since_H_2'] - (df['last_H_2'] - df['low_since_H_2']).abs() * rm
        )
    
        df['ST_Short'] = np.where(
            long_mask,
            df['high_since_L_2'] + (df['high_since_L_2'] - df['last_L_2']).abs() * rm,
            df['last_H_2'] + df['swing_2'].abs() * rm
        )
    
        # --------------------------------------------------
        # 6. Risk metrics
        # --------------------------------------------------
        df['KO_Long'] = close - df['ST_Long']
        df['KO_Short'] = df['ST_Short'] - close
    
        df['Risk_Long'] = df['KO_Long'] / close * 100
        df['Risk_Short'] = df['KO_Short'] / close * 100
    
        # --------------------------------------------------
        # 7. ✅ IMPORTANT FIX: row-wise boolean instead of scalar
        # --------------------------------------------------
        df['Risk_Long_Adm'] = df['KO_Long'] < swing_up_mean
        df['Risk_Short_Adm'] = df['KO_Short'] < swing_down_mean
    
        return df

    
    def signals_vectorized(self,df):

        df = df.copy()
        # --- Conditions ---
        long_cond = (df["BOS"] == "UP")
        short_cond = (df["BOS"] == "DOWN")

        # --- Raw signals (vectorized) ---
        df.loc[:, "raw_signal"] = np.where(long_cond, "LONG",
                            np.where(short_cond, "SHORT", None))

        # --- Remove duplicates (stateful, minimal loop) ---
        signals = df["raw_signal"].values
        final = [None] * len(signals)

        last = None
        for i in range(len(signals)):
            s = signals[i]
            if s is not None and s != last:
                final[i] = s
                last = s

        df.loc[:, "signal"] = final

        # optional cleanup
        df.drop(columns=["raw_signal"], inplace=True)

        return df
    
    def tradable_signals(self,df):

        df = df.copy() 
        # --- Conditions ---
        long_confirmed = ((df["signal"] == "LONG") & (df["Tradable"] == True) & (df['Over_Bought_Sold'] == "BUY"))
    
        short_confirmed = ((df["signal"] == "SHORT") & (df["Tradable"] == True) & (df['Over_Bought_Sold'] == "SELL"))


        # --- Raw signals (vectorized) ---
        df.loc[:, "confirmed_signal"] = np.where(long_confirmed, "GO LONG",
                            np.where(short_confirmed, "GO SHORT", None))

        return df

    def future_return(self, df):
        """
        Calculate maximum returns from each LONG signal until the next stop hit candle.
        
        For each LONG signal:
        - Find the entry price (close price at LONG signal)
        - Find the next stop loss hit candle
        - Calculate the maximum high between LONG and stop loss hit (max return)
        - Calculate the P50 percentile of highs (realistic return expectations)

        Similarly for each SHORT signal
        """
        df = df.copy()
        
        # Initialize new columns
        df.loc[:, 'run-up'] = np.nan
        df.loc[:, 'draw-down'] = np.nan
        
        # Get indices of LONG and SHORT signals
        long_indices = df[df['confirmed_signal'] == 'GO LONG'].index.tolist()
        short_indices = df[df['confirmed_signal'] == 'GO SHORT'].index.tolist()
        
        for long_idx in long_indices:
            # Find next SHORT signal after this LONG
            next_shorts = [s for s in short_indices if s > long_idx]
            # Find next stop loss hit candle after this LONG
            stop_long_hit = df[df['low'] <= df.loc[long_idx, 'ST_Long']].index.tolist()
            candidates = [ s for s in stop_long_hit if s > long_idx]
            next_stop_hit = min(candidates) if candidates else None
            
            if next_stop_hit:
                next_stop_hitt_idx = next_stop_hit[0]
                
                # Get entry price (close at LONG signal)
                entry_price = df.loc[long_idx, 'close']

                # Get run-up between LONG and Stop Loss
                price_high_range = df.loc[long_idx:next_stop_hit_idx, 'high'].values
                
                # Calculate MAX runup and drawdown (distance, not percentage)
                max_high = np.max(price_high_range)
                max_runup = max_high - entry_price
                max_drawdown = entry_price - df.loc[long_idx, 'ST_Long']

                # Store results
                df.loc[long_idx, 'run-up'] = max_runup
                df.loc[long_idx, 'draw-down'] = max_drawdown


        for short_idx in short_indices:
            # Find next LONG signal after this SHORT
            next_longs = [s for s in long_indices if s > short_idx]
            # Find next stop loss hit candle after this SHORT
            stop_short_hit = df[df['high'] >= df[short_idx,'ST_Short']].index.tolist()
            candidates = [ s for s in stop_short_hit if s > short_idx]
            next_stop_hit = min(candidates) if candidates else None
            
            if next_longs:
                next_stop_hit_idx = next_stop_hit[0]
                
                # Get entry price (close at SHORT signal)
                entry_price = df.loc[short_idx, 'close']
                
                # Get price range between LONG and SHORT
                price_low_range = df.loc[short_idx:next_stop_hit_idx, 'low'].values
                
                # Calculate MAX draw-down (distance, not percentage)
                min_low = np.min(price_low_range)
                max_runup = df[short_idx,'ST_Short'] - entry_price
                max_drawdown = entry_price - min_low

                # Store results
                df.loc[short_idx, 'run-up'] = max_runup
                df.loc[short_idx, 'draw-down'] = max_drawdown


        # Export signals to CSV after processing all signals
        subset_long = df[df['signal'] == 'LONG']
        subset_long.to_csv("DAX_Long_Signal_Data.csv", index=True)
        #print(subset_long[['time', 'close', 'future_long_return', 'p50_future_long_return', 'ST_Long_distance']].tail(5))

        subset_short = df[df['signal'] == 'SHORT']
        subset_short.to_csv("DAX_Short_Signal_Data.csv", index=True)        
        #print(subset_short[['time', 'close', 'future_short_return', 'p50_future_short_return', 'ST_Short_distance']].tail(5))
        
        return df
    
    def StochasticTradable(self, df):

        df = df.copy()

        df.loc[:, 'Tentative'] = "NONE"
        df.loc[:, 'Tradable'] = False
        df.loc[:, 'P50_stop_loss'] = np.nan
        df.loc[:, 'Risk-Reward-Ratio'] = np.nan
    
         
        if df["dir_tf"].iloc[-1] == -1:
            df_5Y = pd.read_csv("DAX_Long_Signal_Data.csv")

            runups = df_5Y["run-up"].dropna()
            drawdowns = df_5Y["draw-down"].dropna()

            P50_stop_loss = df['close'].iloc[-1] - (drawdowns).mean() 
            df.loc[:, 'P50_stop_loss'] = P50_stop_loss

            RRR = (runups).mean() / (drawdowns).mean() if (drawdowns).mean() != 0 else np.inf
            df.loc[:, 'Risk-Reward-Ratio'] = RRR
            
        elif df["dir_tf"].iloc[-1] == 1:
            df_5Y = pd.read_csv("DAX_Short_Signal_Data.csv")

            runups = df_5Y["run-up"].dropna()
            drawdowns = df_5Y["draw-down"].dropna()
            
            P50_stop_loss = (runups).mean() + df['close'].iloc[-1]
            df.loc[:, 'P50_stop_loss'] = P50_stop_loss
            
            RRR = (drawdowns).mean() / (runups).mean() if (runups).mean() != 0 else np.inf
            df.loc[:, 'Risk-Reward-Ratio'] = RRR

        else:
            return df

        if df["dir_tf"].iloc[-1] == -1:
            df.loc[:, 'Tentative'] = "LONG"
            if RRR >= 1 and P50_stop_loss < df['ST_Long'].iloc[-1]:
                df.loc[:, 'Tradable'] = True
                
        elif df["dir_tf"].iloc[-1] == 1:
            df.loc[:, 'Tentative'] = "SHORT"
            if RRR >= 1 and P50_stop_loss > df['ST_Short'].iloc[-1]:
                df.loc[:, 'Tradable'] = True
                
        return df
    
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

        df.loc[:,'wpr_D'] = self.wpr(df_1d, 40)
        
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

        return df

    def Over_Bought_Sold(df):
        df.loc[:, 'Over_Bought_Sold'] = np.nan
    
        TradableLong = False
        TradableShort = False
    
        # Condiciones (esto es vectorial en pandas)
        if (df['EMA8'] > df['upperBand']).any():
            TradableLong = False
            TradableShort = True
    
        if TradableShort and (df['confirmed_signal'] == "GO SHORT").any():
            TradableShort = False
    
        if (df['EMA8'] < df['lowerBand']).any():
            TradableLong = True
            TradableShort = False
    
        if TradableLong and (df['confirmed_signal'] == "GO LONG").any():
            TradableLong = False
    
        if TradableLong:
            df.loc[:, 'Over_Bought_Sold'] = "SELL"
        elif TradableShort:
            df.loc[:, 'Over_Bought_Sold'] = "BUY"
        else:
            df.loc[:, 'Over_Bought_Sold'] = "Not Applicable"
    
        return df

    def Trend(df):
        df = df.copy()
    
        df['LT_Trend'] = "Not Applicable"
    
        # LONG condition
        df.loc[df['wpr_D'] >= -28, 'LT_Trend'] = "BULLISH"
    
        # SHORT condition
        df.loc[df['wpr_D'] <= -72, 'LT_Trend'] = "BEARISH"
    
        # Middle zone
        mid_zone = (df['wpr_D'] > -72) & (df['wpr_D'] < -28)
    
        # Use diff correctly (must call it!)
        rising = df['wpr_D'].diff() > 0
        falling = df['wpr_D'].diff() < 0
    
        df.loc[mid_zone & rising, 'LT_Trend'] = "BULLISH"
        df.loc[mid_zone & falling, 'LT_Trend'] = "BEARISH"

        return df

        
    def Back_Test_Signals(self, df, buffer, RM):

        df = df.copy()
        df = self.main_indicator(df)
        df = self.multi_timeframe_zigzag(df1, df2):
        df = self.BOS_detection(df, buffer=3)
        df = self.SL_RA(df, RM=10)
        df = self.Over_Bought_Sold (df)
        df = self.SR_Daily_levels(df3,2,2)
        df = self.signals_vectorized(df)
        df = self.future_return(df)

        return df
    
    def Real_time_signals(self, df, buffer, RM):
        
        df = df.copy()
        df = self.main_indicator(df)
        df = self.Over_Bought_Sold (df)
        df = self.SR_Daily_levels(df,2,2)
        df = self.HFMS_vectorized(df, left=1, right=1, buffer=buffer)
        df = self.TFMS_vectorized(df, left=40, right=40, RM=RM, shift_pivots=False)
        df = self.signals_vectorized(df)
        df = self.StochasticTradable(df)
        df = self.tradable_signals(df)
   
        return df
    
