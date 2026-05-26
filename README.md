IBAPI python framework
Request historical data for last 5D in 3min and 1H timeframe, create both dataframe df_3M and df_H
Optionally request for the last 30D in 1D and create df_D dataframe
Market signals and parameters are computed in signal_engine class. It is feed with the three dataframe.
Entry signals and order setting are coming from signal_engine class and managed on 3min bar close.  All entry orders will be limit order with stop loss but without take profit.
Profit target is coming from signal_engine. If price hit profit target, stop loss is updated to break even on every tick
Exit signals are coming from signal_engine class and checked on every tick. Exit orders will be market.
