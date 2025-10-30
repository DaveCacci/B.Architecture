Davide Carecci 02.07.2025

OS is Raspbian ARM 64bit. Run `neofetch` in terminal to see properties.

The python interpreter and package manager in miniforge3. The `base` environment automatically activates when starting a terminal.

To run any python file (i.e. $filename.py) related to AD control in BioTA lab, run in terminal: 
```conda activate adcontrol``` 
```cd /home/santiagogarciagen/NMPC```
```python $filename.py```

You can download a copy of the controller library from `https://github.com/DaveCacci/NMPC` when it will be made available.

To install the required python packages, see `/home/santiagogarciagen/python_requirements.txt`, and to install them, for each $packagename, run in terminal:
```conda install -n adcontrol $packagename```
If you want a specific version $packageversion, run instead: 
```conda install -n adcontrol $packagename == $packageversion```
NOTE You can check which packages are already installed by running:
```conda activate adcontrol``` 
```conda list``` 

Follow the instructions to setup the relay, creating another folder `/home/santiagogarciagen/RPI_Relay_Board`. 
A subfolder of this called `python` can be used to place the python files that set the PWM of the actuators (e.g. pwm_set_R1.py).