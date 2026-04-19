import pandas as pd
import threading

df_live = pd.DataFrame()
lock = threading.Lock()

def update_data(new_row):
    global df_live
    with lock:
        df_live = pd.concat([df_live, new_row]).tail(440)

def get_data():
    with lock:
        return df_live.copy()