import numpy as np
import pandas as pd
from Market_Signals import SignalEngine


df = pd.read_csv("DAX_Raw_Data.csv", index_col=0)

df = SignalEngine().Back_Test_Signals(df,3,10)   

df.to_csv("DAX_Back_Test_Data.csv", index=True)