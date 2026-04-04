import pandas as pd
import os
import numpy as np

cache = pd.read_parquet('dataset/dynamic_events_pl_24/_pressing_cache.parquet',
    columns=['match_id', 'team_shortname', 'pressing_chain', 'pressing_chain_index', 
             'attacking_side', 'x_start', 'frame_start', 'frame_end'])

chains = cache[cache['pressing_chain'] == True].copy()
flip = chains['attacking_side'] == 'left_to_right'
chains['x_norm'] = np.where(flip, -chains['x_start'], chains['x_start'])

opp_half = chains[(chains['x_norm'] > 0) & (chains['match_id'] == 1650385)]
unique = opp_half.drop_duplicates(subset=['match_id', 'team_shortname', 'pressing_chain_index'], keep='first')

print(f'Unique opp half chains: {len(unique)}')

if len(unique) > 0:
    chain_row = unique.iloc[0]
    pressing_team = chain_row['team_shortname']
    chain_start = int(chain_row['frame_start'])
    chain_end = int(chain_row['frame_end'])
    print(f'Chain: team={pressing_team}, frame {chain_start}-{chain_end}')
    
    mf = pd.read_parquet('dataset/dynamic_events_pl_24/dynamic/1650385.parquet',
        columns=['event_type', 'pass_outcome', 'end_type', 'x_start', 'attacking_side', 'frame_start', 'pass_range', 'team_shortname'])
    
    flip = mf['attacking_side'] == 'left_to_right'
    mf['x_norm'] = np.where(flip, -mf['x_start'], mf['x_start'])
    
    opp_passes = mf[
        (mf['event_type'] == 'player_possession') &
        (mf['end_type'] == 'pass') &
        (mf['team_shortname'] != pressing_team) &
        (mf['x_norm'] > 0) &
        (mf['pass_range'].isin(['medium', 'long'])) &
        (mf['frame_start'] >= chain_start) &
        (mf['frame_start'] <= chain_end)
    ]
    print(f'Passes found: {len(opp_passes)}')
    if len(opp_passes) > 0:
        print('Outcomes:', opp_passes['pass_outcome'].value_counts().to_dict())
    else:
        print('No passes found. Checking broader window...')
        test = mf[(mf['team_shortname'] != pressing_team) & (mf['end_type'] == 'pass')]
        print(f'Total opp passes in match: {len(test)}')
        print(f'Opp passes in opp half: {len(test[test["x_norm"] > 0])}')
        print(f'Medium/long: {len(test[(test["x_norm"] > 0) & (test["pass_range"].isin(["medium", "long"]))])}')
        
        # Check frame range
        print(f'Frame range in match: {mf["frame_start"].min()} - {mf["frame_start"].max()}')
        print(f'Chain window: {chain_start} - {chain_end}')
