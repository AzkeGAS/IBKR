
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
        df.loc[:, 'EMA8'] = hlc4.ewm(span=8).mean()
        df.loc[:, 'EMA155'] = hlc4.ewm(span=155).mean()

        # ---- Bands ----
        std155 = hlc4.rolling(155).std()
        df.loc[:, 'UpperBand'] = df['EMA155'] + 2 * std155
        df.loc[:, 'LowerBand'] = df['EMA155'] - 2 * std155


        # ---- Trend (spread EMA) ----
        ema123 = hlc4.ewm(span=123).mean()
        ema188 = hlc4.ewm(span=188).mean()
        trend = (ema123 - ema188).ewm(span=2).mean()
        df.loc[:, 'Trend'] = trend

        # ---- Velocity & Acceleration (suavizado) ----
        vel = trend.pct_change().ewm(span=2).mean()
        df.loc[:, 'Velocity'] = vel
        df.loc[:, 'Acceleration'] = vel.diff()

        # ---- WPR ----
        df.loc[:, 'wpr'] = self.wpr(df, 40)
        df.loc[:, 'wpr_lf'] = self.wpr(df, 800)

        return df

    # =========================
    # High frequency ZigZag and BOS check
    # =========================

    def HFMS_vectorized(self, df, left=1, right=1, buffer=3):

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

    # =========================
    # Low frequency ZigZag and Risk assessment
    # =========================
    def TFMS_vectorized(self, df, left=40, right=40, RM=10, shift_pivots=True):


        df = df.copy()
        window = left + right + 1

        # --------------------------------------------------
        # 1. Detectar pivots (raw)
        # --------------------------------------------------
        rolling_max = df['high'].rolling(window, center=True).max()
        rolling_min = df['low'].rolling(window, center=True).min()

        df.loc[:, 'H_raw'] = np.where(
            (df['high'] == rolling_max) &
            (df['high'] > df['high'].shift(1)),
            df['high'], np.nan
        )

        df.loc[:, 'L_raw'] = np.where(
            (df['low'] == rolling_min) &
            (df['low'] < df['low'].shift(1)),
            df['low'], np.nan
        )

        # --------------------------------------------------
        # 2. Quitar lookahead (backtest real)
        # --------------------------------------------------
        if shift_pivots:
            df.loc[:, 'H_raw'] = df.loc[:, 'H_raw'].shift(right)
            df.loc[:, 'L_raw'] = df.loc[:, 'L_raw'].shift(right)

        # --------------------------------------------------
        # 3. Combinar pivots
        # --------------------------------------------------
        pivot_type = np.where(df['H_raw'].notna(), 'H',
                    np.where(df['L_raw'].notna(), 'L', None))

        pivot_price = np.where(df['H_raw'].notna(), df['H_raw'],
                    np.where(df['L_raw'].notna(), df['L_raw'], np.nan))

        # --------------------------------------------------
        # 4. FILTRO DE ALTERNANCIA (CORE)
        # --------------------------------------------------
        filtered_type = [None] * len(df)
        filtered_price = [np.nan] * len(df)

        last_type = None
        last_price = None
        last_idx = None

        for i in range(len(df)):

            t = pivot_type[i]
            p = pivot_price[i]

            if t is None:
                continue

            # --- primer pivot: SOLO L ---
            if last_type is None:
                if t == 'L':
                    filtered_type[i] = 'L'
                    filtered_price[i] = p
                    last_type = 'L'
                    last_price = p
                    last_idx = i
                continue

            # --- alternancia ---
            if t != last_type:
                filtered_type[i] = t
                filtered_price[i] = p
                last_type = t
                last_price = p
                last_idx = i

            else:
                # --- mismo tipo → mantener extremo ---
                if t == 'H' and p > last_price:
                    filtered_type[last_idx] = None
                    filtered_price[last_idx] = np.nan

                    filtered_type[i] = 'H'
                    filtered_price[i] = p

                    last_price = p
                    last_idx = i

                elif t == 'L' and p < last_price:
                    filtered_type[last_idx] = None
                    filtered_price[last_idx] = np.nan

                    filtered_type[i] = 'L'
                    filtered_price[i] = p

                    last_price = p
                    last_idx = i

        # --------------------------------------------------
        # 5. Reconstrucción final
        # --------------------------------------------------
        df.loc[:, 'H_tf'] = np.where(np.array(filtered_type) == 'H', filtered_price, np.nan)
        df.loc[:, 'L_tf'] = np.where(np.array(filtered_type) == 'L', filtered_price, np.nan)


        # --------------------------------------------------
        # 6. Índices y dirección
        # --------------------------------------------------
        idx = np.arange(len(df))

        df.loc[:, 'H_idx_tf'] = np.where(df.loc[:, 'H_tf'].notna(), idx, np.nan)
        df.loc[:, 'L_idx_tf'] = np.where(df.loc[:, 'L_tf'].notna(), idx, np.nan)

        df.loc[:, 'H_idx_tf'] = df.loc[:, 'H_idx_tf'].ffill()
        df.loc[:, 'L_idx_tf'] = df.loc[:, 'L_idx_tf'].ffill()

        df.loc[:, 'dir_tf'] = np.where(df.loc[:, 'H_idx_tf'] > df.loc[:, 'L_idx_tf'], 1, -1)

        # --------------------------------------------------
        # 7. Últimos pivots
        # --------------------------------------------------
        df.loc[:, 'last_H_tf'] = df.loc[:, 'H_tf'].ffill()
        df.loc[:, 'last_L_tf'] = df.loc[:, 'L_tf'].ffill()

        # --- Extremes since pivot (SAFE replacement of future lookups) ---
        df.loc[:, 'low_since_H'] = df['low'].groupby(df['H_idx_tf']).cummin()
        df.loc[:, 'high_since_L'] = df['high'].groupby(df['L_idx_tf']).cummax()

        # --- Swing ---
        df.loc[:, 'swing_tf'] =  df['last_H_tf'] - df['last_L_tf']

        df.loc[:, 'swing_H_tf'] = np.where(np.array(filtered_type) == 'H', df['last_H_tf'] - df['last_L_tf'], np.nan)
        df.loc[:, 'swing_L_tf'] = np.where(np.array(filtered_type) == 'L', -df['last_H_tf'] + df['last_L_tf'], np.nan)
        
        swing_up_mean = df['swing_H_tf'].dropna().mean()/2
        print(swing_up_mean)
        swing_down_mean = df['swing_L_tf'].dropna().mean()/2
        print(swing_down_mean)

        rm = RM / 100
        close = df['close']

        # --- Stops ---
        long_mask = df['dir_tf'] == 1

        df.loc[:, 'ST_Long'] = np.where(
            long_mask,
            df['last_L_tf'] - abs(df['last_H_tf'] - df['last_L_tf']) * rm,
            df['low_since_H'] - abs(df['last_H_tf'] - df['low_since_H']) * rm  
        )

        df.loc[:, 'ST_Short'] = np.where(
            long_mask,
            df['high_since_L'] + abs(df['last_H_tf'] - df['high_since_L']) * rm,
            df['last_H_tf'] + abs(df['last_H_tf'] - df['last_L_tf']) * rm
        )

        # --- Risk ---
        df.loc[:, 'KO_Long'] = (close - df['ST_Long']) 
        df.loc[:, 'KO_Short'] = (df['ST_Short'] - close)
        df.loc[:, 'Risk_Long'] = (close - df['ST_Long']) / close * 100
        df.loc[:, 'Risk_Short'] = (df['ST_Short'] - close) / close * 100
        
        df.loc[:, 'Risk_Long_Adm'] = True if df.loc[:, 'KO_Long'].iloc[-1] < swing_up_mean else False
        df.loc[:, 'Risk_Short_Adm'] = True if df.loc[:, 'KO_Short'].iloc[-1] < swing_down_mean else False

        return df
    
    def signals_vectorized(self,df):

        df = df.copy()
        # --- Conditions ---
        long_cond = (
            (df["BOS"] == "UP") &
            (
                (df["Risk_Long_Adm"] == True) |
                (df["dir_tf"] == -1)
            )
        )

        short_cond = (
            (df["BOS"] == "DOWN") &
            (
                (df["Risk_Short_Adm"] == True) |
                (df["dir_tf"] == 1)
            )
        )

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
        long_confirmed = ((df["signal"] == "LONG") & (df["Tradable"] == True))
    
        short_confirmed = ((df["signal"] == "SHORT") & (df["Tradable"] == True))


        # --- Raw signals (vectorized) ---
        df.loc[:, "confirmed_signal"] = np.where(long_confirmed, "GO LONG",
                            np.where(short_confirmed, "GO SHORT", None))

        return df

    def future_return(self, df):
        """
        Calculate maximum future returns from each LONG signal until the next SHORT signal.
        
        For each LONG signal:
        - Find the entry price (close price at LONG signal)
        - Find the next SHORT signal
        - Calculate the maximum high between LONG and SHORT (max return)
        - Calculate the P50 percentile of highs (realistic return expectations)
        - Compute returns as price distance (not percentage)
        
        Returns:
            df with new columns:
            - 'future_long_return': max distance return from LONG entry to max high
            - 'p50_future_long_return': 50th percentile distance return from LONG to SHORT
            - 'ST_distance': distance from current close to stop loss (ST_Short)
        """
        df = df.copy()
        
        # Initialize new columns
        df.loc[:, 'run-up'] = np.nan
        df.loc[:, 'draw-down'] = np.nan
        
        # Get indices of LONG and SHORT signals
        long_indices = df[df['signal'] == 'LONG'].index.tolist()
        short_indices = df[df['signal'] == 'SHORT'].index.tolist()
        
        for long_idx in long_indices:
            # Find next SHORT signal after this LONG
            next_shorts = [s for s in short_indices if s > long_idx]
            
            if next_shorts:
                next_short_idx = next_shorts[0]
                
                # Get entry price (close at LONG signal)
                entry_price = df.loc[long_idx, 'close']
                
                # Get price range between LONG and SHORT
                price_high_range = df.loc[long_idx:next_short_idx, 'high'].values
                price_low_range = df.loc[long_idx:next_short_idx, 'low'].values
                
                # Calculate MAX runup and drawdown (distance, not percentage)
                max_high = np.max(price_high_range)
                max_runup = max_high - entry_price

                min_low = np.min(price_low_range)
                max_drawdown = entry_price - min_low

                # Store results
                df.loc[long_idx, 'run-up'] = max_runup
                df.loc[long_idx, 'draw-down'] = max_drawdown


        for short_idx in short_indices:
            # Find next LONG signal after this SHORT
            next_longs = [s for s in long_indices if s > short_idx]
            
            if next_longs:
                next_long_idx = next_longs[0]
                
                # Get entry price (close at SHORT signal)
                entry_price = df.loc[short_idx, 'close']
                
                # Get price range between LONG and SHORT
                price_high_range = df.loc[short_idx:next_long_idx, 'high'].values
                price_low_range = df.loc[short_idx:next_long_idx, 'low'].values
                
                # Calculate MAX runup and draw-down (distance, not percentage)
                max_high = np.max(price_high_range)
                max_runup = max_high - entry_price

                min_low = np.min(price_low_range)
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
    
    def Back_Test_Signals(self, df, buffer, RM):

        df = df.copy()
        df = self.main_indicator(df)
        df = self.HFMS_vectorized(df, left=1, right=1, buffer=buffer)
        df = self.TFMS_vectorized(df, left=40, right=40, RM=RM, shift_pivots=False)
        df = self.signals_vectorized(df)
        df = self.future_return(df)

        return df
    
    def Real_time_signals(self, df, buffer, RM):
        
        df = df.copy()
        df = self.main_indicator(df)
        df = self.HFMS_vectorized(df, left=1, right=1, buffer=buffer)
        df = self.TFMS_vectorized(df, left=40, right=40, RM=RM, shift_pivots=False)
        df = self.signals_vectorized(df)
        df = self.StochasticTradable(df)
        df = self.tradable_signals(df)
        df = self.SR_Daily_levels(df,2,2)
   
        return df
    