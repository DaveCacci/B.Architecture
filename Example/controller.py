# COMMON PRELIMINARIES #######################################################################################
#------------------------------------------------------------------------------------------------------------#
# Common standard python libraries that are needed
import numpy as np
import logging
import os
import pandas as pd
from datetime import datetime, timedelta
import sys

sys.path.insert(0, '...') #Add the path to the 'controller' library is (in order to place this .py in a specific subfolder)
sys.path.insert(0, '...') #Add the path to the 'preprocess_meas.py'  
#------------------------------------------------------------------------------------------------------------#
# Common functions from the 'NMPC' library
import process_parameters as pp
from save_df import*
from convert_u_to_pwm import* 
#------------------------------------------------------------------------------------------------------------#
def main(modelname):
    # DECLARE SIMULATION META-OPTIONS
    testname = ''
    directory = os.getcwd()
    #------------------------------------------------------------------------------------------------------------#
    # DECLARE LOGGER
    # Configure logging
    log_directory = os.path.join(directory, testname, "logs")
    os.makedirs(log_directory, exist_ok=True)
    log_file = os.path.join(log_directory, 'openloop_logging.log')
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
    logger.info('############################################### START MAIN ###############################################')
    #------------------------------------------------------------------------------------------------------------#
    # READ INTEGRATOR.JSON 
    import process_parameters as pp
    theta = {}
    theta_path = os.path.join(directory, testname, f'integrator_{modelname}.json')
    theta['integrator_parameters'] = pp.load_parameters(theta_path)
    logging.info(f'Integrator parameters are present for: {theta["integrator_parameters"].keys()}')
    integrator_parameters = theta['integrator_parameters']
    integrator_parameters['nmpc']['start_timestamp'] = datetime.strptime(integrator_parameters['model']['start_timestamp'], "%Y-%m-%d %H:%M:%S")

    # Load the preprocessed data
    y_df_on_path = os.path.join(directory, testname, 'awite', f'y_df_data_on_alt_R{modelname}.csv')
    y_df_data_on = pd.read_csv(y_df_on_path, sep=',', header=0, parse_dates=['Timestamp'])
    # Keep only the specified columns in y_df_data_on
    y_df_data_on = y_df_data_on[['Timestamp', 'gas_rate', 'xM_gb_out', 'xC_gb_out']] #xC_gb_out xM_gb_out
    # Compute some quantities 
    y_df_data_on['ch4_rate'] = y_df_data_on['gas_rate']*y_df_data_on['xM_gb_out']
    y_df_data_on['co2_rate'] = y_df_data_on['gas_rate']*y_df_data_on['xC_gb_out']
    y_df_data_on['co2ch4'] = y_df_data_on['xC_gb_out']/y_df_data_on['xM_gb_out']
    #------------------------------------------------------------------------------------------------------------#
    # Your controller here <--------------------------------------------#
    #------------------------------------------------------------------------------------------------------------#
    # Write the control action
    # CONVERT CONTROL ACTION TO ON/OFF TIMES FOR THE RASPBERRY PI RELAY
    u_current = 100 #mL/day
    u_max = 400 #mL/day
    dt = 6*3600 #seconds
    pump_dose_per_minute = 20 #mL/min
    period = 19 #sec
    tuple_seconds_ini, on_periods_tot, conversion_error = convert_u_to_pwm(u_current, u_max, dt, pump_dose_per_minute, period)
    rounded_dosage = period*on_periods_tot*pump_dose_per_minute/60*24/dt*3600 #mL/day
    pwm_star_dict = dict(zip(['on_sec', 'off_sec', 'tot_on_periods', 'rounded_dosage'],
                    np.array([tuple_seconds_ini[0], tuple_seconds_ini[1], on_periods_tot, rounded_dosage])))
    pwm_star_df = pd.DataFrame([pwm_star_dict]) #duplicate last element
    pwm_star_df.insert(0, 'Timestamp', integrator_parameters['nmpc']['start_timestamp'])
    save_df_with_check(pwm_star_df, os.path.join(directory, testname, "Input", f'NMPC_R1_pwm_actual_ACNILLARY.csv'), log=True) #save with date_string?
    #------------------------------------------------------------------------------------------------------------#
    logger.info('############################################### END MAIN ###############################################')
#------------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    # Allow the script to be executed from the terminal
    if len(sys.argv) != 2:
        print("Usage: python Chile_preprocess_model_EKF_openloop.py <modelname>")
        sys.exit(1)

    modelname = sys.argv[1]
    main(modelname)
