import numpy as np
import pandas as pd

def extract_swings(df):
    df = df.copy()

    # Collect pivots into one series
    pivots = pd.concat([
        df[['H']].dropna().rename(columns={'H': 'price'}),
        df[['L']].dropna().rename(columns={'L': 'price'})
    ]).sort_index()

    pivots['type'] = np.where(pivots.index.isin(df[df['H'].notna()].index), 'H', 'L')

    # Remove duplicates (if H and L happen same bar)
    pivots = pivots[~pivots.index.duplicated(keep='first')]

    # Shift to create swing legs
    pivots['next_price'] = pivots['price'].shift(-1)
    pivots['next_type'] = pivots['type'].shift(-1)
    pivots['next_idx'] = pivots.index.to_series().shift(-1)

    # Keep only valid alternating swings
    swings = pivots.dropna()

    return swings

def classify_swings(swings):
    swings = swings.copy()

    swings['direction'] = np.where(
        (swings['type'] == 'L') & (swings['next_type'] == 'H'),
        'bull',
        np.where(
            (swings['type'] == 'H') & (swings['next_type'] == 'L'),
            'bear',
            'invalid'
        )
    )

    swings = swings[swings['direction'] != 'invalid']

    return swings

def compute_swing_metrics(swings):
    swings = swings.copy()

    # Price move
    swings['points'] = swings['next_price'] - swings['price']

    # Absolute move
    swings['abs_points'] = swings['points'].abs()

    # Percentage move
    swings['pct_move'] = swings['points'] / swings['price'] * 100

    # Duration (bars)
    swings['duration'] = swings['next_idx'] - swings.index

    # Fix sign for bearish
    swings.loc[swings['direction'] == 'bear', 'points'] *= -1

    return swings

def swing_statistics(swings):
    stats = {}

    for d in ['bull', 'bear']:
        subset = swings[swings['direction'] == d]

        stats[d] = {
            'count': len(subset),
            'avg_move': subset['points'].mean(),
            'median_move': subset['points'].median(),
            'volatitiy_move': subset['points'].stdv(),
            'max_move': subset['points'].max(),
            'min_move': subset['points'].min(),
            'avg_pct': subset['pct_move'].mean(),
            'avg_duration': subset['duration'].mean(),
            'win_rate': (subset['points'] > 0).mean()
        }

    return pd.DataFrame(stats)

df_hfms = HFMS_vectorized(df)
swings = extract_swings(df_hfms)
swings = classify_swings(swings)
swings = compute_swing_metrics(swings)

stats = swing_statistics(swings)
