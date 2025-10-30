import pandas as pd
from datetime import datetime, timedelta

def sample_df(df, freq):

    sample_timestamps = []
    current_time = df['Timestamp'].min()
    while current_time <= df['Timestamp'].max():
        sample_timestamps.append(current_time)
        current_time += timedelta(hours=freq)
    # Filter the DataFrame based on the created list of timestamps
    df_filtered = df[df['Timestamp'].isin(sample_timestamps)]
    
    return df_filtered