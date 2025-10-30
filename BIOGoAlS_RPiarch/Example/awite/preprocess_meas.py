# Script to convert register data to y_on data readable by controller
# Modify the input_path and output_path variables to match the desired input and output file paths
# Modify the start_timestamp and end_timestamp variables to match the desired time range (filter out register data to decrease computation time)
# Modify the range of the for loop to match the number of CSTRs
# Modify log=True to log=False if you do not want to log warnings about dropped rows due to NaN values

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
sys.path.insert(0, '...') #Add the path to the 'controller' library is (in order to place this .py in a specific subfolder)
from save_df import save_df_with_check
from from_register_to_data import*
from from_data_to_y import*

def main():
    # DECLARE LOGGER
    # Configure logging
    log_directory = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_directory, exist_ok=True)
    log_file = os.path.join(log_directory, 'preprocess_logging.log')
    logger = logging.getLogger()
    # File handler for writing logs to a file
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)

    if not logger.handlers:  # Avoid duplicate handlers
        # Console handler for displaying logs in the terminal
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        # Add handlers to the logger
        logger.addHandler(console_handler)

    logger.setLevel(logging.INFO)
    logger.info('############################################### START PREPROCESS ###############################################')
    # --------------------------------------------------- #
    now = datetime.now()
    # Round to the nearest hour
    now = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1 if now.minute >= 30 else 0)
    start_timestamp = now - timedelta(days=2, minutes=5) # THIS MUST BE HIGHER THAN THE WIDTH OF THE MOVING AVERAGE WINDOW
    end_timestamp = now
    log = True
    logger.info(f"Running preprocess_meas.py from {start_timestamp} to {now}...")

    for i in range(2): # <--- Change this to the number of CSTRs
        # Define the folder containing the raw data files
        raw_data_folder = os.getcwd()
        output_path = os.path.join(os.getcwd(), f'data_R{i+1}.csv')
        # Generate the list of files for the current CSTR
        cstr_files = [f for f in os.listdir(raw_data_folder)
            if f.startswith(f'CSTR_{i+1}_') and f.endswith('.csv')]
        # Filter files based on the date range
        relevant_files = []
        for file in cstr_files:
            try:
                # Extract the date from the filename (e.g., CSTR_1_2025-03-28.csv)
                file_date_str = file.split('_')[-1].replace('.csv', '')
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                if start_timestamp.date() <= file_date.date() <= end_timestamp.date():
                    relevant_files.append((file, file_date))  # Store file with its date
            except ValueError:
                logger.warning(f"Skipping file with invalid date format: {file}")

        # Sort relevant files by date
        relevant_files.sort(key=lambda x: x[1])  # Sort by the extracted date
        relevant_files = [file[0] for file in relevant_files]  # Extract only filenames

        # Concatenate data from all relevant files
        concatenated_df = pd.DataFrame()
        for file in relevant_files:
            input_path = os.path.join(raw_data_folder, file)
            df = pd.read_csv(input_path)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            concatenated_df = pd.concat([concatenated_df, df], ignore_index=True)
        # Filter the concatenated DataFrame by the timestamp range
        concatenated_df = concatenated_df[(concatenated_df['Timestamp'] >= start_timestamp) & (concatenated_df['Timestamp'] <= end_timestamp)]

        # Check the life counter
        check_life_counter(concatenated_df)
        # Convert the registers to data
        concatenated_df.reset_index(drop=True, inplace=True)
        df = from_registers_to_data('',concatenated_df)
        # Save the resulting DataFrame to a new CSV file
        save_df_with_check(df, output_path, log=False)
        # Drop rows that are not needed anymore 
        df = df.drop(columns=['Timestamp_raw','timestamp_diff','life_counter','level bag','counter','life_counter_diff'])
        # Drop rows with NaN values and issue a warning if any rows are dropped
        before_dropna_count = len(df)
        df = df.dropna()
        after_dropna_count = len(df)
        dropped_rows_count = before_dropna_count - after_dropna_count
        if dropped_rows_count > 0 and log==True:
            logging.warning(f"Warning: {dropped_rows_count} rows were dropped due to NaN values.")

        # Convert the data to the y_data_on that can be read by the controller
        keys = ['Timestamp','gas_rate','xM_gb','xC_gb']
        df = df[keys]
        df.reset_index(drop=True, inplace=True)
        y_df_data_on_all = from_data_to_y('', df)
        df = y_df_data_on_all[-1] #grouped df
        output_path = "..." # <---------------------------------------------------- Change this to the desired output path
        # Drop rows with NaN values and issue a warning if any rows are dropped
        before_dropna_count = len(df)
        df = df.dropna()
        after_dropna_count = len(df)
        dropped_rows_count = before_dropna_count - after_dropna_count
        if dropped_rows_count > 0 and log==True:
            logging.warning(f"Warning: {dropped_rows_count} rows were dropped due to NaN values.")
        # Save the resulting DataFrame to a new CSV file
        save_df_with_check(df, os.path.join(output_path, f'y_df_data_on_R{i+1}.csv'), log=True)
        # Save a copy of df to a new file (overwrite the previous one if existing, this is the one used by the controller)
        columns_to_round = df.columns.difference(['Timestamp', 'time'], sort=False) #Round everything but for Timestamp and time columns if present
        df[columns_to_round] = df[columns_to_round].round(5)
        df.to_csv(os.path.join(output_path, f'y_df_data_on_R{i+1}_lastdays.csv'), index=False)

        # Save also y_data_on_raw for the computation of the COD balance (offline)
        df = y_df_data_on_all[1] #grouped df
        output_path =  os.path.join(os.getcwd(),f'y_df_data_on_raw_R{i+1}.csv')
        # Drop rows with NaN values and issue a warning if any rows are dropped
        before_dropna_count = len(df)
        df = df.dropna()
        after_dropna_count = len(df)
        dropped_rows_count = before_dropna_count - after_dropna_count
        if dropped_rows_count > 0 and log==True:
            logging.warning(f"Warning: {dropped_rows_count} rows were dropped due to NaN values.")
        # Save the resulting DataFrame to a new CSV file
        save_df_with_check(df, output_path, log=False)
        
        # Save also y_data_on_alternative
        df = y_df_data_on_all[-2] # moving average, outliers removed with treshold=3, interpolation of gas compositions
        output_path =  os.path.join(os.getcwd(),f'y_df_data_on_alt_R{i+1}.csv')
        # Drop rows with NaN values and issue a warning if any rows are dropped
        before_dropna_count = len(df)
        df = df.dropna()
        after_dropna_count = len(df)
        dropped_rows_count = before_dropna_count - after_dropna_count
        if dropped_rows_count > 0 and log==True:
            logging.warning(f"Warning: {dropped_rows_count} rows were dropped due to NaN values.")
        # Save the resulting DataFrame to a new CSV file
        save_df_with_check(df, output_path, log=False)
        
    logger.info("Measurements were preprocessed")
    logger.info('############################################### END PREPROCESS ###############################################')
    
if __name__ == "__main__":
    # Allow the script to be executed from the terminal
    if len(sys.argv) != 1:
        print("Usage: python preprocess_meas.py <>")
        sys.exit(1)
    main()
