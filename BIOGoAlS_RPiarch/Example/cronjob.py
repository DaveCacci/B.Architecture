# Script to check if a new gas analysis is available in the raw 'register' data read from modbus
# THIS CODE RUNS EVERY HOUR at HH:01 (cronjob) AND CHECKS IF A NEW MEASUREMENT IS AVAILABLE
# IF A NEW MEASUREMENT IS AVAILABLE, IT RUNS THE NMPC (if the hour is in the list of hours to check)

# Modify the input_path and output_path variables to match the desired input and output file paths
# Modify the start_timestamp and end_timestamp variables to match the desired time range (filter out register data to decrease computation time)
# Modify the range of the for loop to match the number of CSTRs
# Modify log=True to log=False if you do not want to log warnings about dropped rows due to NaN values
# Modify the nmpc_nominal_interval variable to match the desired time interval for running NMPC (default is 6 hours)
#------------------------------------------------------------------------------------------------------------#
import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, '...') #Add the path to the 'controller' library is (in order to place this .py in a specific subfolder)
sys.path.insert(0, '...') #Add the path to the 'preprocess_meas.py'   
from preprocess_meas import main as preprocess_main
from sample_df import *
from process_parameters import*
from controller import main
#------------------------------------------------------------------------------------------------------------#
# Preprocess measurement data
# Change temporaily the directory to save results
original_dir = os.getcwd()  # Store the current directory
temp_dir = os.path.join(original_dir, 'awite')
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)
os.chdir(temp_dir)  # Change to the save directory
logging.info(f"Current working directory is now: {os.getcwd()}. Running preprocess_meas.py...")

preprocess_main()

# Change back directory to the original one
os.chdir(original_dir)  # Change back to the original directory
logging.info(f"Current working directory is now: {os.getcwd()}. Terminated preprocess_meas.py...")

# Shut down the logger present in preprocess_meas
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.shutdown()
#-------------------------------------------------------------------------------#
# DECLARE LOGGER
# Configure logging
log_directory = os.path.join(os.getcwd(), "logs")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, 'cronjob_logging.log')
logger = logging.getLogger()
# Clean up any existing handlers for this logger
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
    handler.close()
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
logger.info('############################################### START CRONJOB ###############################################')
#-------------------------------------------------------------------------------#
now = datetime.now()
# Round to the nearest hour (modified on 28.03.2025?)
now = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1 if now.minute >= 30 else 0)
start_timestamp = now - timedelta(days=2)  # THIS MUST BE HIGHER THAN THE WIDTH OF THE MOVING AVERAGE WINDOW (and rounded to the nearest hour)
end_timestamp = now
log = True
modelname = '1'  # <---------------------------------- or '2' i.e. which reactor number?
nmpc_nominal_interval = timedelta(hours=6)  # 6 hours
#-------------------------------------------------------------------------------#
# Step 1: Get the last run time
last_run_file = f"last_NMPC_run_time_R{modelname}.txt"
if os.path.exists(last_run_file):
    with open(last_run_file, "r") as f:
        # Read all lines and get the last non-empty line
        lines = f.readlines()
        if lines:
            # Split the last line into timestamp and status
            last_line = lines[-1].strip().split(",")
            last_run_time = datetime.strptime(last_line[0], "%Y-%m-%d %H:%M:%S")
            last_status = last_line[1] if len(last_line) > 1 else "unknown"
            logger.info(f"Last run time: {last_run_time}, Status: {last_status}")
            # Find the last run time with status 'ok'
            last_run_time_withok = None
            for line in lines:
                parts = line.strip().split(",")
                if len(parts) == 2 and parts[1] == "ok":
                    last_run_time_withok = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")

            if last_run_time_withok and last_run_time == last_run_time_withok:
                logger.info(f"Last run time matches the last successful run time: {last_run_time_withok}")
            else:
                logger.warning(f"Last run time ({last_run_time}) does not match the last successful run time ({last_run_time_withok}). Using the last unsuccessful run time.")
            if last_run_time_withok is None:
                last_run_time_withok = last_run_time
                logger.warning(f"Last run time with status 'ok' not found. Defaulting to last run time: {last_run_time_withok}.")
        else:
            last_run_time = datetime.min  # Default to a very old time if the file is empty
            last_run_time_withok = datetime.min
            logger.warning(f"{last_run_file} is empty. Defaulting to {last_run_time}.")
            logger.warning(f"Last run time with status 'ok' is not available. Defaulting to {last_run_time_withok}.")
else:
    last_run_time = datetime.min  # Default to a very old time if file doesn't exist
    last_run_time_withok = datetime.min
    logger.warning(f"{last_run_file} not found. Defaulting to {last_run_time}.")
    logger.warning(f"Last run time with status 'ok' is not available. Defaulting to {last_run_time_withok}.")
#-------------------------------------------------------------------------------#
# Step 2: Check the latest measurement timestamp in the CSV
# Define the folder containing the raw data files
raw_data_folder = os.path.join(os.getcwd(), 'awite')
output_path = os.path.join(os.getcwd(), f'data_R{modelname}.csv')
# Generate the list of files for the current CSTR
cstr_files = [f for f in os.listdir(raw_data_folder)
                if f.startswith(f'CSTR_{modelname}_') and f.endswith('.csv')]
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

# Sample at every 1 (rounded) hour
df_sampled = sample_df(concatenated_df, 1)
# Check if the difference in some columns is greater than 0.1
df_sampled['CH4_diff'] = df_sampled['CH4'].diff()
df_sampled['CO2_diff'] = df_sampled['CO2'].diff()
#-------------------------------------------------------------------------------#
# Step 3: Determine if NMPC should run
should_run_nmpc = False
last_hour = df_sampled['Timestamp'].iloc[-1].to_pydatetime()

# Check if at least one diff between df_sampled['CH4', 'CO2'] at iloc[-1] and at Timestamp == last_run_time is different from 0
last_run_row = df_sampled[df_sampled['Timestamp'] == last_run_time]
last_run_withok_row = df_sampled[df_sampled['Timestamp'] == last_run_time_withok]
if not last_run_withok_row.empty:
    ch4_diff = df_sampled['CH4'].iloc[-1] - last_run_withok_row['CH4'].iloc[0]
    co2_diff = df_sampled['CO2'].iloc[-1] - last_run_withok_row['CO2'].iloc[0]
    if (abs(ch4_diff) > 0 or abs(co2_diff) > 0) and last_hour > last_run_time:
        logger.info(f"Difference detected wrt last_run hour: CH4_diff={ch4_diff}, CO2_diff={co2_diff}")
        logger.info(f"New meas available at {df_sampled['Timestamp'].iloc[-1]}. Running NMPC...")
        should_run_nmpc = True
    else:
        logger.info("No significant difference detected in CH4 or CO2.")  
else:
    logger.warning(f"No data found for last_run_time: {last_run_time}, trying to check the last row.")
    if df_sampled[['CH4_diff', 'CO2_diff']].iloc[-1].ne(0).any() and last_hour > last_run_time:
        logger.info(f"Difference detected wrt previous hour: CH4_diff={df_sampled['CH4_diff'].iloc[-1]}, CO2_diff={df_sampled['CO2_diff'].iloc[-1]}")
        logger.info(f"New meas available at {df_sampled['Timestamp'].iloc[-1]}. Running NMPC...")
        should_run_nmpc = True

    #df_sampled[['CH4_diff', 'CO2_diff']].iloc[-1].ne(0).any() and last_hour > last_run_time:
if should_run_nmpc == False and now - last_run_time >= nmpc_nominal_interval:
    logger.info(f"{nmpc_nominal_interval} hours have passed since the last NMPC run. Running NMPC...")
    should_run_nmpc = True
elif should_run_nmpc == False and now - last_run_time < nmpc_nominal_interval:
    logger.info("No new measurement and less than 6 hours since last run. Skipping NMPC.")
#-------------------------------------------------------------------------------#
# Step 4: Run NMPC if conditions are met
if should_run_nmpc:
    try:
        # Create a dictionary with last_run_time and now
        old_integratorjson = load_parameters('integrator.json')
        integrator_parameters = {}
        integrator_parameters['model'] = {
            "start_timestamp": last_run_time_withok,
            "end_timestamp": now # I can't use last_hour becouse there can be present holes in the register data. However, preprocess_meas.py shall fill.
        }
        integrator_parameters['ekf'] = {
            "start_timestamp": last_run_time_withok,
            "end_timestamp": now
        }
        integrator_parameters['nmpc'] = {
            "start_timestamp": now,
            "end_timestamp": now + timedelta(hours=old_integratorjson['nmpc']['control_interval']*10)  # 10 is the number of control intervals in the prediction horizon
        }
        update_parameters('integrator.json', integrator_parameters['model'],'model', log=True)
        update_parameters('integrator.json', integrator_parameters['ekf'],'ekf', log=True)
        update_parameters('integrator.json', integrator_parameters['nmpc'],'nmpc', log=True)
        logger.info(f"integrator.json with old timestamps: {old_integratorjson['model']}")
        logger.info(f"Updated integrator.json with new timestamps: {integrator_parameters['model']}")

        # Call your NMPC function or script here
        logger.info("Running NMPC...")
        modelname = str(modelname)
        main(modelname)

        # Simulate NMPC execution (replace with actual NMPC call)
        # If NMPC runs successfully, set status to 'ok'
        status = "ok"
    except Exception as e:
        # Log the error and set status to 'error'
        logger.error(f"NMPC execution failed: {e}", exc_info=True)  # Log stack trace
        status = "error"

    # Update the last run time
    with open(last_run_file, "a") as f:  # Open in append mode
        f.write(f"{now.strftime('%Y-%m-%d %H:%M:%S')},{status}\n")
    logger.info(f"NMPC executed at {now}. Status: {status}. Last run time updated.")
else:
    logger.info("NMPC was not executed as conditions were not met.")
logger.info('############################################### END CRONJOB ###############################################')
