import numpy as np
import pandas as pd
import logging

def outlier_removal(df, column_name, threshold=3):
    # Compute the mean and standard deviation
    mean_value = df[column_name].mean()
    std_value = df[column_name].std()

    # Check if the standard deviation is zero
    if std_value == 0:
        df.loc[:, f'Z-score_{column_name}'] = 0
    else:
        # Compute the Z-score
        df.loc[:, f'Z-score_{column_name}'] = np.abs((df[column_name] - mean_value) / std_value)
    
    # Find indices of outliers
    outlier_indices = np.where(df[f'Z-score_{column_name}'] > threshold)[0]
    logging.info(f'Found {len(outlier_indices)} outliers in {column_name}: {outlier_indices}')
    df.loc[:, f'{column_name}_out'] = df[column_name]

    # Replace outliers with linear interpolation
    for idx in outlier_indices:
        prev_idx = idx - 1
        next_idx = idx + 1

        # Handle the case where the first element is an outlier
        if prev_idx < 0:
            first_valid_idx = next(i for i in range(len(df)) if i not in outlier_indices)
            logging.info(
                f'First index {idx} is an outlier in {column_name}. '
                f'Original value: {df.at[idx, column_name]}, '
                f'substituted with value: {df.at[first_valid_idx, column_name]} '
                f'(first_valid_idx: {first_valid_idx}).'
            )
            df.at[idx, f'{column_name}_out'] = df.at[first_valid_idx, f'{column_name}_out']
            continue

        # Handle the case where the last element is an outlier
        while next_idx in outlier_indices:
            next_idx += 1
        if next_idx >= len(df):
            last_valid_idx = next(i for i in range(len(df) - 1, -1, -1) if i not in outlier_indices)
            logging.info(
                f'Last index {idx} is an outlier in {column_name}. '
                f'Original value: {df.at[idx, column_name]}, '
                f'substituted with value: {df.at[last_valid_idx, column_name]} '
                f'(last_valid_idx: {last_valid_idx}).'
            )
            df.at[idx, f'{column_name}_out'] = df.at[last_valid_idx, f'{column_name}_out']
            continue

        # Interpolate the value
        interpolated_value = df.at[prev_idx, f'{column_name}_out'] + (
            (idx - prev_idx) * (df.at[next_idx, f'{column_name}_out'] - df.at[prev_idx, f'{column_name}_out'])
        ) / (next_idx - prev_idx)
        df.at[idx, f'{column_name}_out'] = interpolated_value

    return df

def moving_average(df, column_name, window_size=3):
    '''
    Calculate the moving average of a column in a dataframe. Window size is the number of data points to include in the average.
    '''
    df_ma = df.copy()
    df_ma.loc[:,f'{column_name}_ma'] = df_ma[column_name].rolling(window=window_size).mean()
    return df_ma

def smooth_gas_compositions(df, column_name):
    '''
    Column name is the name of the column to be smoothed (single column!!)
    Smooth the data by removing duplicates and performing linear interpolation.
    The values returned must be subtituted to the original column in the dataframe i.e. do "df[column_name] = smooth(df)" outside!!
    '''
    # Convert the 'Timestamp' column to datetime
    df.loc[:,'Timestamp'] = pd.to_datetime(df['Timestamp'])
    # Set 'time' as the index
    df.set_index('Timestamp', inplace=True)
    # Filter out consecutive duplicate values
    df.loc[:,'diff'] = df[column_name].diff()
    filtered_df = df[(df['diff'] > 0.001) | (df['diff'] < -0.001)]
    # Add again first row
    filtered_df = pd.concat([df.iloc[0:1], filtered_df])
    # Perform linear interpolation
    interpolated_df = filtered_df.reindex(df.index).interpolate(method='linear')
    
    return interpolated_df[column_name].values

def groupby_time_interval(df, column_names, time_interval='5T', aggregation='mean', multiplier=1):
    """
    Group the DataFrame by a specified time interval and aggregate the specified columns.

    Parameters:
    df (pd.DataFrame): Input DataFrame with a 'Timestamp' column.
    column_names (list): List of column names to aggregate (expect the 'Timestamp' column).
    time_interval (str): Time interval for grouping (e.g., '5T' for 5 minutes, '150T' for 150 minutes, '1H' for 1 hour, 'D' for date).
    aggregation (str): Aggregation method (e.g., 'mean', 'sum').

    Returns:
    pd.DataFrame: DataFrame grouped by the specified time interval with aggregated columns.
    """
    # Ensure the 'Timestamp' column is in datetime format
    df.loc[:,'Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Calculate the expected count based on the time_interval
    time_interval_minutes = pd.to_timedelta(time_interval).total_seconds() / 60
    expected_count = time_interval_minutes / 5 #5 minutes interval is the default!!
    # Check if any group has a different count from the expected count
    group_counts = df.groupby(pd.Grouper(key='Timestamp', freq=time_interval)).size()
    invalid_groups = group_counts[group_counts != expected_count]
    if not invalid_groups.empty:
        logging.warning(f"Warning: The number of elements in some groups is different from {expected_count}. Group indices: {invalid_groups.index.tolist()}")

    # Group by the specified time interval and aggregate the specified columns
    if aggregation == 'mean':
        grouped_df = df.groupby(pd.Grouper(key='Timestamp', freq=time_interval)).mean().reset_index()
    elif aggregation == 'sum':
        grouped_df = df.groupby(pd.Grouper(key='Timestamp', freq=time_interval)).sum().reset_index()
    else:
        raise ValueError(f"Unsupported aggregation method: {aggregation}")
    # Multiply by multipliers
    grouped_df[column_names] = grouped_df[column_names]*multiplier

    # Select only the 'Timestamp' column and the specified columns
    grouped_df = grouped_df[['Timestamp'] + column_names]

    return grouped_df

def from_data_to_y(input_path, df = None, time_interval='1H', aggregation='mean', multiplier=1):
    '''
    Create the target variable y from the data. The target variable is the next value in the time series.
    '''
    if df is None:
        df = pd.read_csv(input_path)
        
    df_out = outlier_removal(df, 'gas_rate', threshold=6) #any other? pH online? Temperature?
    df_out = outlier_removal(df_out, 'xM_gb', threshold=6) #any other? pH online? Temperature?
    df_out = outlier_removal(df_out, 'xC_gb', threshold=6) #any other? pH online? Temperature?
    df_out_ma = moving_average(df_out, 'gas_rate_out', window_size=12) #groupby after moving_average or not?? 17.03.2025 Groupby yes, moving average not used!!
    df_out_ma_interp = df_out_ma.copy()
    df_out_ma_interp['xch4_interp'] = smooth_gas_compositions(df_out_ma.copy(), 'xM_gb_out')
    df_out_ma_interp['xco2_interp'] = smooth_gas_compositions(df_out_ma.copy(), 'xC_gb_out')

    # Create a new dataframe before grouping otherwise saving 'gas_rate' I'm not actually saving the 'gas_rate_out'
    df_input_grouping = df_out_ma_interp.copy()
    df_input_grouping.loc[:,'gas_rate'] = df_out_ma_interp['gas_rate_out']
    df_out_ma_interp_grouped = groupby_time_interval(df_input_grouping, ['gas_rate', 'xch4_interp', 'xco2_interp'], 
                                                     time_interval=time_interval, aggregation=aggregation, multiplier=multiplier)
    
    # Compute also ch4_rate, co2_rate and gas_ratio?
    
    return df, df_out, df_out_ma, df_out_ma_interp, df_out_ma_interp_grouped

# Function to compute other aggregated quantities

def cumulate_values_in_range(df, value_col, start_time, end_time):
    # Ensure the timestamp column is of type datetime64[ns]
    df.loc[:,'Timestamp'] = pd.to_datetime(df['Timestamp'])
    # Filter the DataFrame based on the specified timestamp range
    filtered_df = df[(df['Timestamp'] >= start_time) & (df['Timestamp'] <= end_time)]
    # Cumulate values in the specified range
    cumulated_value = filtered_df[value_col].sum()
    logging.info(f'Cumulated value of {value_col} between {start_time} and {end_time}: {cumulated_value}')

    return cumulated_value

def compute_cod(df, column_name, codvs_ratio):
    df.loc[:,f'{column_name}_cod'] = df[column_name] * codvs_ratio
    return df

def compute_mean_stdev(df, start_timestamp, end_timestamp, column_names):
    # Compute the mean
    filtered_df = df[(df['Timestamp'] >= start_timestamp) & (df['Timestamp'] <= end_timestamp)]
    result_dict = {}
    for column_name in column_names:
        mean_value = filtered_df[column_name].mean()
        std_dev_value  = filtered_df[column_name].std()
        logging.info(f"The mean value between {start_timestamp} and {end_timestamp} of {column_name} is: {mean_value} with st.dev: {std_dev_value}")
        result_dict[column_name] = (mean_value, std_dev_value)
    return result_dict
