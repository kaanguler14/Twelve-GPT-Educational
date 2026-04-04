import pandas as pd
import os
import numpy as np

# Get associated event IDs
cache = pd.read_parquet('dataset/dynamic_events_pl_24/_pressing_cache.parquet',
    columns=['match_id', 'team_shortname', 'associated_player_possession_event_id', 'pressing_chain', 'x_start', 'attacking_side'])

chains = cache[cache['pressing_chain'] == True].copy()
sample_match = 1650385
sample = chains[chains['match_id'] == sample_match]

assoc_ids = set(sample[sample['associated_player_possession_event_id'].notna()]['associated_player_possession_event_id'].values)
print(f'Associated IDs: {len(assoc_ids)}')

# Load match and check all associated
mf = pd.read_parquet(f'dataset/dynamic_events_pl_24/dynamic/{sample_match}.parquet',
    columns=['event_id', 'pass_outcome', 'pass_range', 'end_type', 'x_start', 'attacking_side', 'team_shortname'])

# Normalize
flip = mf['attacking_side'] == 'left_to_right'
mf['x_norm'] = np.where(flip, -mf['x_start'], mf['x_start'])

# Get all associated
associated = mf[mf['event_id'].isin(assoc_ids)].copy()
print(f'Total: {len(associated)}, successful: {len(associated[associated["pass_outcome"] == "successful"])}, unsuccessful: {len(associated[associated["pass_outcome"] == "unsuccessful"])}')

# Apply filters one by one
print('\nApplying filters:')
press_relevant = associated[associated['end_type'] == 'pass']
print(f'After end_type=pass: {len(press_relevant)}')

relevant_opp_half = press_relevant[press_relevant['x_norm'] > 0]
print(f'After x_norm > 0: {len(relevant_opp_half)}')

relevant_range = relevant_opp_half[relevant_opp_half['pass_range'].isin(['medium', 'long'])]
print(f'After pass_range [medium, long]: {len(relevant_range)}')
if len(relevant_range) > 0:
    print('  - Unsuccessful:', len(relevant_range[relevant_range['pass_outcome'] == 'unsuccessful']))

print('\nAll associated unsuccessful passes (pre-filter):')
unsuccessful_all = associated[associated['pass_outcome'] == 'unsuccessful']
print(f'Count: {len(unsuccessful_all)}')
print(f'  pass_range distribution: {unsuccessful_all["pass_range"].value_counts().to_dict()}')
print(f'  x_norm > 0: {len(unsuccessful_all[unsuccessful_all["x_norm"] > 0])}')
print(f'  In medium/long: {len(unsuccessful_all[(unsuccessful_all["x_norm"] > 0) & (unsuccessful_all["pass_range"].isin(["medium", "long"]))])}')
