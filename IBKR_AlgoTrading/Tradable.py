
import pandas as pd
if df['signal'] == "Long"
  df_6M = pd.read_csv("DAX_Long_signals_Data.csv")
  runups = df_6M["runup"].dropna()
  drawdowns = df_6M["drawdown"].dropna()
  stop_points = df['ST_Long']
elif df['signal'] == "Short"
  df_6M = pd.read_csv("DAX_Short_signals_Data.csv")
  runups = df_6M["runup"].dropna()
  drawdowns = df_6M["drawdown"].dropna()
  stop_points = df['ST_Short']
else
  return

# Probability  Profit and Stop exceed the target
P_profit_hit = (runups > stop_points).mean()
P_stop_hit = (drawdowns > stop_points).mean()

if P_profit_hit >= P_stop_hit and P_stop_hit <= 0.5
  df['Tadrable'] = "True"
  print("Signal sthocastically tradable")
