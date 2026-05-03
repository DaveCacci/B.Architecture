## Created on 19.05.2025 by Davide Carecci 
Inscructions on how to run the closed-loop control in real-time on the Raspberry RPi connected with an Awite biogas analyzer (that "collects" also the data of the biogas flow rate) via Modbus.

---

### General note
The "connections" between the files, the "blood" of this very simple controller structure is the use of "Timestamp" column in dataframes and files, correctly formatted. 

- TO BE RUN FROM TERMINAL (in the "...\Example\awite" directory):
    - `modbus3.py`
    - `pwm_set_R1.py`
- TO BE RUN WITH CRONJOB EVERY HH AT HH:01 (in the "...\Example" directory):
    - `cronjob.py`

---

### Data-read side
- With `modbus3.py` in the `\awite` subfolder you read raw registers data and write like `CSTR_1_2025_05_06.csv` (it does reading for both reactors R1 and R2).
- `preprocess_meas.py` in the `\awite` subfolder reads raw CSV files and preprocesses them (for both R1 and R2 reactors). It uses the `from_register_to_data.py` and `from_data_to_y.py` Python codes/functions. The "first step" of preprocessing is returned as `data_R1.csv`. The last step that will be read by the controller is as `y_df_data_on_alt_R1.csv` (see below).

---

### Controller
- `cronjob.py` checks every hour if the controller shall run or not. If `True`, it calls `controller.py` (`modelname` is the number of the reactor you want to perform control on, as string).
- In `controller.py` the `convert_u_to_pwm.py` function converts the control action in g d$^{-1}$ to ON/OFF duty cycles of the peristaltic pumps (as pulse width modulation (PWM).

---

### Control action side
- `NMPC_R1_pwm_actual_ANCILLARY.csv` in the `\Input` subfolder is where the output of the controller is written, and read by the code that sets the RPi GPIO pins of the pump (`pwm_set_R1.py`).

---

### Example usage
To run an ++off-line example++ with the ++provided data files++: 
- put the content of the this repository into the desired path. The main current working directory will be `yourpath\\Example` (open terminals from here to subfolders, and add `yourpath` inside the Python files where the `...` placeholder is present);
- also, modify the system path to be added and specify eventual desired input/output folder paths;
- modify row 46 of `preprocess_meas.py` with `now = datetime(2025,5,8,12,0)`;
- do the same in row 76 of `cronjob.py`;
