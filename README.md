# LED matrix app

See a demo here: https://www.youtube.com/watch?v=TyzOgKOoLEo



## Setup

**Install dependencies**

```bash
sudo apt install libffi-dev libbz2-dev liblzma-dev libsqlite3-dev libncurses5-dev libgdbm-dev zlib1g-dev libreadline-dev libssl-dev tk-dev build-essential libncursesw5-dev libc6-dev openssl git libopenblas-dev
chmod +x scripts/install_python3_6.sh # install python3.6
curl -O https://bootstrap.pypa.io/get-pip.py; sudo python3.6 get-pip.py # install pip
# Alternatively, create a virtual environment first `python3.6 -m venv venv/`
python3.6 -m pip install spidev flask adafruit-circuitpython-bitbangio adafruit-circuitpython-busdevice
```
*Note*: Installing these packages system wide is bad practice. Standard practice would be to use a virtual environment. In my defence, nothing else on the pi is going to be running python3.6. 


**Setup app to run on startup**


Better way:
``` bash
chmod +x run.sh

# $ crontab -e
@reboot /home/jm/Desktop/led-matrix-app/run.sh
```



Easy, bad way: Add the following line to *.bashrc*
```bash
alias ledmatrixquickstart="cd Desktop/led-matrix-app; source venv/bin/activate"
source /home/jm/Desktop/led-matrix-app/venv/bin/activate && python3 /home/jm/Desktop/led-matrix-app/app.py >> /home/jm/Desktop/led-matrix-app/log.txt
```

## Development

tail logs from heroku: `heroku logs --app jeremysmorgan --tail`