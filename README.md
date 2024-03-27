# ubseds-ground-station

This is the revamped UB SEDS ground station. 
It takes data in the form of packets from the radio and displays the information from the packets in various ways:
1. The Kalman velocity, acceleration, and alititde data is displayed in graphs
2. Pressure and temperature is displayed with gauges
3. Latitude and longitude data is displayed with an openlayers
4. Rest of the data is displayed in various cards

To get started, clone this repo and make sure you have Python 3.12 installed.

In windows command prompt or Apple/Linux terminal:
```
python3 --version
```
should give Python 3.12.X

Then create the virtual environment in which the flask server will be ran. If you are using VSCode, make sure you have the python extension installed. Then open the command palette and type "Python: Create Environment". Select .venv, and install requirements.txt. 
Then in you terminal, type in 
```
python -m app
```
and click on the link, it should bring you to your defualt brower and open the ground station.
