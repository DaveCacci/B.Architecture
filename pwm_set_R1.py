import os
import csv
import time
import threading
import hashlib
import pandas as pd
import RPi.GPIO as GPIO
from datetime import datetime
import signal
import sys

# File Paths
CSV_FILE_PATH = ".../Input/NMPC_R1_pwm_actual_ANCILLARY.csv" # <----- substitute with your actual file path
PUMP_LOG_FILE = "pump_status_log_R1.csv"

# Relay GPIO Pin
Relay_Ch1 = 26 #CH1: 26; CH2: 20; CH3: 21

# Timing Variables
high_time = 10  # Default HIGH time (seconds)
low_time = 0   # Default LOW time (seconds)

# File Monitoring Parameters
TIME_THRESHOLD = 300  # 5 minutes in seconds
pwm_update_event = threading.Event()

# GPIO Setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(Relay_Ch1, GPIO.OUT)
GPIO.output(Relay_Ch1, GPIO.HIGH)  # Ensure circuit is initially open (relay OFF)

print("Setup The Relay Module is [success]")

# Function to log pump status changes
def log_pump_status(status):
    """ Append pump status (1 = ON, 0 = OFF) with timestamp to CSV file. """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PUMP_LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, status])
    print(f"Logged pump status: {status} at {timestamp}")

# Function to monitor the CSV file for updates
def watch_file():
    """ Continuously watches the CSV file for changes and updates PWM values. """
    global high_time, low_time
    last_hash = None

    while True:
        if os.path.exists(CSV_FILE_PATH):
            try:
                # Read only the last row of the CSV file
                df = pd.read_csv(CSV_FILE_PATH)
                if not df.empty:
                    last_row = df.iloc[-1]  # Get last row
                    timestamp_str = last_row["Timestamp"]
                    new_low_time = float(last_row["on_sec"])
                    new_high_time = float(last_row["off_sec"])

                    # Convert timestamp from string to datetime
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        print(f"Warning: Invalid timestamp format in CSV: {timestamp_str}")
                        time.sleep(15)  # Wait before next check
                        continue

                    # Check time difference
                    now = datetime.now()
                    time_diff = abs((now - timestamp).total_seconds())

                    # Create a hash to check for changes
                    new_hash = hashlib.md5(f"{timestamp},{new_low_time},{new_high_time}".encode()).hexdigest()

                    if new_hash != last_hash:  # Detect change
                        if time_diff > TIME_THRESHOLD:
                            print(f"?? Warning: Last CSV update is far ({time_diff/60:.1f} minutes from now).")

                        high_time, low_time = new_high_time, new_low_time
                        print(f"CSV change detected: HIGH {high_time}s, LOW {low_time}s (Timestamp: {timestamp})")

                        pwm_update_event.set()  # Signal the PWM loop to update immediately
                        last_hash = new_hash  # Store the latest hash

            except Exception as e:
                print(f"Error reading CSV: {e}")

        time.sleep(15)  # Check every TIME_THRESHOLD for updates

# Function to control the relay as PWM
def relay_pwm():
    global high_time, low_time
    while True:
        if low_time > 0:  # Only toggle the relay if high_time > 0
            GPIO.output(Relay_Ch1, GPIO.LOW)
            log_pump_status(1)  # Log ON state
            print("Channel 1: The Common Contact is access to the Normal Open Contact!")
            
            # Respect the full low_time duration
            elapsed_time = 0
            while elapsed_time < low_time:
                time.sleep(1)  # Sleep in 1-second increments
                elapsed_time += 1
                if pwm_update_event.is_set():
                    pwm_update_event.clear()  # Clear the event but continue the current cycle
                    print("PWM update event detected during LOW time. Continuing current cycle.")

            GPIO.output(Relay_Ch1, GPIO.HIGH)
            log_pump_status(0)  # Log OFF state
            print("Channel 1: The Common Contact is access to the Normal Closed Contact!\n")
            
            # Break high_time into 15-second chunks to check for updates
            elapsed_time = 0
            while elapsed_time < high_time:
                sleep_duration = min(15, high_time - elapsed_time)  # Sleep for up to 15 seconds
                time.sleep(sleep_duration)
                elapsed_time += sleep_duration
                if pwm_update_event.is_set():
                    pwm_update_event.clear()  # Clear the event and break the high_time loop
                    print("PWM update event detected during HIGH time. Breaking high_time loop.")
                    break
        else:
            GPIO.output(Relay_Ch1, GPIO.HIGH)  # Keep relay OFF
            log_pump_status(0)  # Log OFF state
            print("Channel 1: circuit is open!\n")
            time.sleep(15)  # Sleep to avoid busy-waiting

# Function to clean up GPIO on exit
def cleanup_gpio():
    """ Ensure the relay is OFF before exiting. """
    GPIO.output(Relay_Ch1, GPIO.HIGH)  # Open circuit (turn relay OFF)
    log_pump_status(0)  # Log that the relay is OFF
    print("\nCleanup: Relay set to OFF (Circuit Open). Exiting...")
    GPIO.cleanup()
    sys.exit(0)

# Catch termination signals (CTRL+C, kill)
signal.signal(signal.SIGINT, lambda sig, frame: cleanup_gpio())  # CTRL+C
signal.signal(signal.SIGTERM, lambda sig, frame: cleanup_gpio())  # Kill command

# Start the PWM thread (it will run continuously)
pwm_thread = threading.Thread(target=relay_pwm, daemon=True)
pwm_thread.start()

# Start the CSV file watcher thread
file_watcher_thread = threading.Thread(target=watch_file, daemon=True)
file_watcher_thread.start()

# Keep the script running
try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    cleanup_gpio()

