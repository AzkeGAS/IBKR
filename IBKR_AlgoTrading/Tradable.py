
import pandas as pd

df_6M = pd.read_csv("DAX_Long_signals_Data.csv")
runups = df_6M["runup"].dropna()
drawdowns = df_6M["drawdown"].dropna()

stop_points = df['ST_Long']

P_take_hit = (runups > stop_points).mean()
P_stop_hit = (drawdowns > stop_points).mean()

if P_take_hit >= P_stop_hit and P_stop_hit <= 0.5
  df['Tadrable'] = "True"
  print("Long tradable:", stop_points)
