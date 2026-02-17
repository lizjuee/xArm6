# xArm Python GUI Controller

A simple desktop GUI to control an **xArm** robot using Python and Tkinter.

## Features

- Connect/disconnect to xArm by IP.
- Enable motion and set mode/state.
- Send joint-space movement commands.
- Send Cartesian pose movement commands.
- Open/close gripper.
- Emergency stop and clear warnings/errors.
- Live status log panel.

## Requirements

- Python 3.10+
- [`xArm-Python-SDK`](https://github.com/xArm-Developer/xArm-Python-SDK)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python xarm_gui.py
```

## Notes

- Ensure your PC can reach the robot IP on the network.
- This app sends direct robot commands; operate in a safe environment.
