import pandas as pd
import numpy as np
import logging

def from_registers_to_data(input_path, df=None, gas_rate_factor = 1/10*3600):
    '''
    This function reads a CSV file containing the registers of a Modbus device and computes the flow rate.
    The original unit of measurements are: [ppm, ppm, 1/100%Vol., 1/10%Vol., 1/10%Vol., 1/1000L, 1/10L]
    The flow rate is computed as: gas_rate = counter_diff / time_diff (time_diff in seconds)
    The gas_rate_factor is used to adjust the unit of measurement of the flow rate (default = (L/h))

    NB gas volume counter is 'counter_'...CORRECT?

    Check if the measurement was read correctly imposing..
    '''
    if df is None:
        # Read the input CSV file
        df = pd.read_csv(input_path, parse_dates=['Timestamp'])
    # Replace invalid data values (e.g., 55553) with NaN
    invalid_value = 55553
    df.replace(invalid_value, np.nan, inplace=True)
    # --------------------------------------------------------------- #
    # Round the Timestamp to the nearest second
    df.insert(1, 'Timestamp_raw', df['Timestamp'].dt.round('S'))
    # Create a new column 'Timestamp_' that rounds 'Timestamp' to the nearest 5-minute interval
    df.loc[:,'Timestamp'] = df['Timestamp'].apply(round_to_nearest_5min)
    # Compute the difference between 'Timestamp_raw' and 'Timestamp' in seconds
    df.insert(2, 'timestamp_diff', (df['Timestamp_raw'] - df['Timestamp']).abs().dt.total_seconds())
    # Check if any difference exceeds 30 seconds
    invalid_rows = df[df['timestamp_diff'] > 30]
    if not invalid_rows.empty:
        row_indices = invalid_rows.index.tolist()
        logging.warning(f"Error: Difference between 'Timestamp_raw' and 'Timestamp' exceeds 30 seconds at row indices: {row_indices}")
    # # Compute the time difference in seconds between consecutive rows
    df.loc[:,'time_diff'] = df['Timestamp'].diff().dt.total_seconds()
    # --------------------------------------------------------------- #
    # Compute the differential of the 'counter' column to obtain the flow rate
    df.loc[:,'counter_diff'] = df['counter_'].diff()
    # Replace negative values in 'counter_diff' with 0
    df.loc[:,'counter_diff'] = df['counter_diff'].apply(lambda x: 0 if x < 0 else x)
    # --------------------------------------------------------------- #
    # Drop the first row because it will have NaN values for the differential and time difference
    #data = df.dropna(subset=['time_diff'])
    data = df.copy()
    # Compute the time difference in seconds between consecutive rows (all but the first row, that has NaN values)
    data.loc[1:,'time_diff'] = data.loc[1:,'time_diff'].round().astype(int)
    # Check if any element in 'time_diff' is not equal to 300 seconds
    #invalid_rows = data[data['time_diff'] != 300]
    # Check if any element in 'time_diff' is not equal to 300 seconds, excluding the first row
    invalid_rows = data.iloc[1:][data['time_diff'] != 300]
    if not invalid_rows.empty:
        row_indices = invalid_rows.index.tolist()
        logging.error(f"Error: 'time_diff' column contains values not equal to 300 seconds at row indices: {row_indices}")
        logging.info("Interpolating missing values linearly...")
        # Create a mesh of timestamps every 5 minutes from the first to the last timestamp in the DataFrame
        start_time = data['Timestamp'].min()
        end_time = data['Timestamp'].max()
        timestamp_mesh = pd.date_range(start=start_time, end=end_time, freq='5T')
        mesh_df = pd.DataFrame({'Timestamp': timestamp_mesh})
        # Merge the original DataFrame with the mesh of timestamps
        df_merged = pd.merge(mesh_df, data, on='Timestamp', how='left')
        # Interpolate the missing values linearly
        columns_to_interpolate = ['counter_', 'CH4', 'CO2', 'H2S','H2','O2']  # Add other columns as needed
        df_merged[columns_to_interpolate] = df_merged[columns_to_interpolate].interpolate(method='linear')
        # Re-compute the time differences
        df_merged.loc[:,'time_diff'] = df_merged['Timestamp'].diff().dt.total_seconds()
        df_merged.loc[:,'counter_diff'] = df_merged['counter_'].diff()
        df_merged.loc[:,'counter_diff'] = df_merged['counter_diff'].apply(lambda x: 0 if x < 0 else x)
        #data = df_merged.dropna(subset=['time_diff'])
        data = df_merged.copy()
        data.loc[1:,'time_diff'] = data.loc[1:,'time_diff'].round().astype(int)
        #invalid_rows = data[data['time_diff'] != 300]
        invalid_rows = data.iloc[1:][data['time_diff'] != 300]
        if not invalid_rows.empty:
            row_indices = invalid_rows.index.tolist()
            logging.error(f"Error: still 'time_diff' column contains values not equal to 300 seconds at row indices: {row_indices}")
            raise ValueError(f"Error: still 'time_diff' column contains values not equal to 300 seconds at row indices: {row_indices}")
    # --------------------------------------------------------------- #
    # Drop the first row because it will have NaN values for the differential and time difference
    data = data.dropna(subset=['time_diff'])
    # Compute the flow rate (counter_diff / time_diff)
    data.loc[:,'gas_rate'] = data['counter_diff'] / data['time_diff']
    # Handle cases where time_diff is zero to avoid infinite values
    data['gas_rate'].replace([float('inf'), -float('inf')], float('nan'), inplace=True)
    # Adjust unit of measurement
    # Adjust gas_rate based on a specific datetime value (before/after the Awite update of 07.04.2025)
    sensor_update = pd.Timestamp("2025-04-07 07:55:00")  # Replace with your desired datetime
    data.loc[data['Timestamp'] < sensor_update, 'gas_rate'] *= gas_rate_factor  # Value for before the datetime
    data.loc[data['Timestamp'] >= sensor_update, 'gas_rate'] *= gas_rate_factor/100  # Value for after the datetime
    # data.loc[:,'gas_rate'] = data['gas_rate'] * gas_rate_factor # As done before the Awite update of 07.04.2025
    data.loc[:,'check'] = data['CH4']/10 + data['CO2']/10
    data.loc[:,'CH4'] = data['CH4']/10 / data['check'] * 100 # rescale to make the sum of CH4 and CO2 equal to 100
    data.loc[:,'CO2'] = data['CO2']/10 / data['check'] * 100 # rescale to make the sum of CH4 and CO2 equal to 100
    data.loc[:,'xM_gb'] = data['CH4']/100
    data.loc[:,'xC_gb'] = data['CO2']/100
    # --------------------------------------------------------------- #

    return data

def check_life_counter(df):
    # Check if the life counter is increasing and not equal to 0
    df.loc[:,'life_counter_diff'] = df['life_counter'].diff()
    if df['life_counter'].iloc[-1] == 0 or df['life_counter_diff'].iloc[-1] == 0:
        logging.warning("Warning: Life counter has not changed or is equal to 0 within the last 5 minutes.")
    else:
        logging.info("Life counter is functioning correctly.")

def round_to_nearest_5min(timestamp):
    # Round the timestamp to the nearest 5-minute interval
    nearest_5min = (timestamp.floor('5T') if timestamp.minute % 5 < 2.5 else timestamp.ceil('5T'))
    return nearest_5min