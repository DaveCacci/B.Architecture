**Author:** Davide Carecci  
**Initial commit:** 01.05.2026  

---

**BIOGoAlS.Architecture** contains the code requried to run the *BIOGoAlS.Twin* controller on a Raspberry Pi (RPi; OS is Raspbian ARM 64bit) equipped with (i) [GPIO RPi Relay Board](https://www.waveshare.com/wiki/RPi_Relay_Board?srsltid=AfmBOor4FJiPsnnBRSH_AKAGjo-DzX5a6obdt5yUby4P_BXRnNl9piWJ), (ii) a peristaltic pump, and (iii) a RJ45 connection between the [Awite biogas analyzer](https://www.awite.de/it/prodotti/analisi-del-gas/awiflex-awiflex-xl/) and the RPi (comumication via Modbus protocol), as it was done during the real-time control experiment carried out between 03-07/2025 at the BioTA lab (Unversidad Federico Santa Maria, Valparaiso, Chile).
For further details about the test facility and equipment, please refer to the [author's PhD thesis](https://polimi365-my.sharepoint.com/:b:/g/personal/10530006_polimi_it/IQB6a8gdnsKrS50a3N5hU4S2AWG3RgSKr8Tnv2vfGtcwvEQ?e=lHCb4G).

The tool:
- pre-processes measurements from the Awite (biogas flow rate and composition);
- computes a control action running a `controller.py`;
- sets the ON/OFF duty cycle of the GPIO relay board to activate/deactivate the power supply to the peristaltic pump;
- recursively at each control interval (or even asynchronously when a new biogas composition measurement is available).

---

### Documentation

- [**Python Requirements**](./python_requirements.txt)  
  List of Python packages required to run the notebooks and scripts in this repository.

- [**Example manual**](./Example_manual.md)  
  Instructions to guide the user to correctly run the content of the `/Example` folder.

---

- **pwm_set_R1.py** Python code used to read and set the ON/OFF duty cycle of the GPIO RPi Relay Board. 

- Other minor custom helper functions.

### Inside the `/Example` folder:

- **controller.py**: Python code that contains the frame in which the user should call its desired controller code (e.g., the `test_closedloop_Chile_main.py` file of the *BIOGoAlS.Twin* repository) to compute the control action. Returns the latter as ON/OFF duty cycle.

- **cronjob.py** Python code that is actually scheduled to run recursively at each control interval or fixed period of time (e.g., each hour). It calls the functions needed to pre-process data, check for the existence of a new biogas composition measurement and, eventually, trigger `controller.py`.

- `/awite` subfolder, that contains:
    - **modbus3.py** Python code needed to read data from Awite analyzer (via Modbus protocol).
    - **preprocess_meas.py** Python code that converts the values read via Modbus and stores them in the proper format to be further read by `controller.py` and `cronjob.py`.
    - Other minor custom helper functions.

- `/Input` subfolder.

---

### Notes
- !! Note that the data of the biogas flow rate (e.g., measured by [Ritter counters](https://www.ritter.de/it/categoria-di-prodotto/milligascounters/)) must be transmitted from the counters to the Awite analyzer, before the information is sent to the RPi. You must contact the Awite support to do this step. 
- Markdown links (`./folder/file`) are used for proper GitHub rendering.  
- Python 3.10+ is required.
- For further details, please refer also to the PhD thesis of the author (visit [POLItesi](https://www.politesi.polimi.it/) or request a copy to <davide.carecci@polimi.it>).
- Run `neofetch` in terminal of the RPi to see properties.
- The python interpreter and package manager in miniforge3. The `base` environment automatically activates when starting a terminal. 
    See basic instructions to create a new virtual environemnt called, for example, `adcontrol`.
- To run any python file (i.e. $filename.py) related to AD control, run in terminal: 
    ```conda activate adcontrol``` 
    ```cd /home/username/NMPC```
    ```python $filename.py```
- You can download a copy of the controller library from `https://github.com/DaveCacci/B.Twin`.
- To install the required python packages, see `/home/username/python_requirements.txt`, and to install them, for each $packagename, run in terminal:
    ```conda install -n adcontrol $packagename```
    If you want a specific version $packageversion, run instead: 
    ```conda install -n adcontrol $packagename == $packageversion```
    NOTE You can check which packages are already installed by running:
    ```conda activate adcontrol``` 
    ```conda list``` 
- Follow the instructions to setup the relay board, creating another folder `/home/username/RPI_Relay_Board`.
    A subfolder of the latter, called `python`, can be used to place the python files that set the PWM of the actuators (e.g., pwm_set_R1.py).

---

© 2026 Davide Carecci — All rights reserved.
