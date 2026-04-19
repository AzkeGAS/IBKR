
PASSWORD = 'your_MSG_password'
API_KEY = 'your_api_key' 
API_SECRET = 'your_secret_key'

import Instruments

# ================== CONFIG ==================

ACCOUNT_SIZE = 25000        # EUR
RPT = float(1.5)            # 1.5 % Risk Per Trade
RB = int(10)                # 10 % Risk Buffer on high timeframe last swing
RRR = float(2.0)            # Risk Reward Ratio 1:2

contract = Instruments.DAX_contract
buffer = Instruments.DAX_buffer

