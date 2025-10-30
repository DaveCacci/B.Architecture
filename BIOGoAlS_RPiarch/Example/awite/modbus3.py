import os
import logging
import sys
import time

# DECLARE LOGGER
# Configure logging
log_directory = os.path.join(os.getcwd(), "")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, 'modbus_logging.log')
# Create handlers
file_handler = logging.FileHandler(log_file, mode='a')  # 'w' for overwrite, 'a' for append
console_handler = logging.StreamHandler()
# Set logging level for handlers
file_handler.setLevel(logging.INFO)
console_handler.setLevel(logging.INFO)
# Create formatter and add it to handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
# Get the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)
# --------------------------------------------------- #

import pandas as pd
from modbus_reader import read_modbus_registers_basic
sys.path.insert(0, '...') #Add the path to the 'controller' library is (in order to place this .py in a specific subfolder)
from save_df import save_df_with_check

# Specify the keys for the values of the registers
keys = ['H2S', 'H2', 'O2', 'CH4', 'CO2', 'level bag', 'counter', 'counter_']
word_types = ['single', 'single', 'single', 'single', 'single', 'single', 'single']

try:
    while True:
        # Get the current timestamp and round it to the nearest past 5-minute mark
        timestamp = pd.Timestamp.now()
        rounded_time = timestamp.floor("5T")  # '5T' means 5 minutes in Pandas

        error_status = read_modbus_registers_basic(802, 1, ['error_status'])
        life_counter = read_modbus_registers_basic(806, 1, ['life counter'])
        value_page = read_modbus_registers_basic(807, 1, ['value page'])

        registers_1 = read_modbus_registers_basic(809, 8, keys)
        registers_2 = read_modbus_registers_basic(817, 8, keys)

        if registers_1:
            df1 = pd.DataFrame({'Timestamp': [timestamp], **registers_1})
            df1.insert(1, 'life_counter', list(life_counter.values()))
            output_path = os.path.join(os.getcwd(), 'CSTR_1.csv')
            save_df_with_check(df1, output_path, log=True)
            logging.info(f'Saved register values to "{output_path}"')
            output_path = os.path.join(os.getcwd(), f'CSTR_1_{timestamp.strftime("%Y-%m-%d")}.csv')
            save_df_with_check(df1, output_path, log=True)
            logging.info(f'Saved register values to "{output_path}"')

        if registers_2:
            df2 = pd.DataFrame({'Timestamp': [timestamp], **registers_2})
            df2.insert(1, 'life_counter', list(life_counter.values()))
            output_path = os.path.join(os.getcwd(), 'CSTR_2.csv')
            save_df_with_check(df2, output_path, log=True)
            logging.info(f'Saved register values to "{output_path}"')
            output_path = os.path.join(os.getcwd(), f'CSTR_2_{timestamp.strftime("%Y-%m-%d")}.csv')
            save_df_with_check(df2, output_path, log=True)
            logging.info(f'Saved register values to "{output_path}"')
            
        # Calculate sleep time until the next 5-minute mark
        next_time = rounded_time + pd.Timedelta(minutes=5)
        sleep_time = max(0, (next_time - pd.Timestamp.now()).total_seconds())

        time.sleep(sleep_time) #Before 15.3.2025 20:55 it waas fixed to 300

except KeyboardInterrupt:
    logging.info("Script interrupted by user.")
    sys.exit(0)
except Exception as e:
    logging.error(f"An error occurred: {e}")
    sys.exit(1)
# --------------------------------------------------- #
