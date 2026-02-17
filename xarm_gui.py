#!/usr/bin/env python3
"""Simple Tkinter GUI for controlling an xArm robot.

This app uses the official xArm Python SDK (`xarm.wrapper.XArmAPI`) when
available. If the SDK is not installed, the UI still starts and guides the
user to install dependencies.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

try:
    from xarm.wrapper import XArmAPI
except Exception:  # noqa: BLE001
    XArmAPI = None


class XArmControllerGUI:
    """Desktop GUI for basic xArm control workflows."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("xArm Controller")
        self.root.geometry("920x620")

        self.arm: Optional["XArmAPI"] = None
        self.polling = False
        self.status_thread: Optional[threading.Thread] = None

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        top = ttk.LabelFrame(container, text="Connection", padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Robot IP:").grid(row=0, column=0, sticky=tk.W)
        self.ip_var = tk.StringVar(value="192.168.1.222")
        ttk.Entry(top, textvariable=self.ip_var, width=20).grid(row=0, column=1, padx=6)

        self.btn_connect = ttk.Button(top, text="Connect", command=self.connect)
        self.btn_connect.grid(row=0, column=2, padx=4)

        self.btn_disconnect = ttk.Button(top, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.btn_disconnect.grid(row=0, column=3, padx=4)

        self.connection_label = ttk.Label(top, text="Not connected", foreground="red")
        self.connection_label.grid(row=0, column=4, padx=8, sticky=tk.W)

        controls = ttk.Frame(container)
        controls.pack(fill=tk.BOTH, expand=True, pady=10)

        left = ttk.LabelFrame(controls, text="Robot Actions", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        ttk.Button(left, text="Enable Motion", command=self.enable_motion).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Set Mode 0 (Position)", command=lambda: self.set_mode(0)).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Set State 0 (Ready)", command=lambda: self.set_state(0)).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Clean Errors", command=self.clean_errors).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Emergency Stop", command=self.emergency_stop).pack(fill=tk.X, pady=2)

        joints_frame = ttk.LabelFrame(left, text="Move Joints (degrees)", padding=8)
        joints_frame.pack(fill=tk.X, pady=8)
        self.joint_vars: list[tk.StringVar] = []
        for i in range(6):
            var = tk.StringVar(value="0")
            self.joint_vars.append(var)
            ttk.Label(joints_frame, text=f"J{i + 1}").grid(row=i // 3, column=(i % 3) * 2, sticky=tk.W)
            ttk.Entry(joints_frame, textvariable=var, width=8).grid(row=i // 3, column=(i % 3) * 2 + 1, padx=(2, 8), pady=2)

        joint_options = ttk.Frame(joints_frame)
        joint_options.grid(row=2, column=0, columnspan=6, sticky=tk.W)
        ttk.Label(joint_options, text="Speed:").pack(side=tk.LEFT)
        self.joint_speed = tk.StringVar(value="20")
        ttk.Entry(joint_options, textvariable=self.joint_speed, width=7).pack(side=tk.LEFT, padx=4)

        ttk.Button(joints_frame, text="Move Joints", command=self.move_joints).grid(row=3, column=0, columnspan=6, sticky=tk.EW, pady=(8, 0))

        cart_frame = ttk.LabelFrame(left, text="Move Cartesian (mm/deg)", padding=8)
        cart_frame.pack(fill=tk.X)
        labels = ["X", "Y", "Z", "Roll", "Pitch", "Yaw"]
        self.cart_vars: list[tk.StringVar] = []
        defaults = ["300", "0", "200", "180", "0", "0"]
        for idx, (name, default) in enumerate(zip(labels, defaults, strict=True)):
            var = tk.StringVar(value=default)
            self.cart_vars.append(var)
            ttk.Label(cart_frame, text=name).grid(row=idx // 3, column=(idx % 3) * 2, sticky=tk.W)
            ttk.Entry(cart_frame, textvariable=var, width=8).grid(row=idx // 3, column=(idx % 3) * 2 + 1, padx=(2, 8), pady=2)

        cart_options = ttk.Frame(cart_frame)
        cart_options.grid(row=2, column=0, columnspan=6, sticky=tk.W)
        ttk.Label(cart_options, text="Speed:").pack(side=tk.LEFT)
        self.cart_speed = tk.StringVar(value="80")
        ttk.Entry(cart_options, textvariable=self.cart_speed, width=7).pack(side=tk.LEFT, padx=4)

        ttk.Button(cart_frame, text="Move Cartesian", command=self.move_cartesian).grid(row=3, column=0, columnspan=6, sticky=tk.EW, pady=(8, 0))

        grip_frame = ttk.LabelFrame(left, text="Gripper", padding=8)
        grip_frame.pack(fill=tk.X, pady=8)
        ttk.Button(grip_frame, text="Open Gripper", command=lambda: self.set_gripper(800)).pack(side=tk.LEFT, padx=4)
        ttk.Button(grip_frame, text="Close Gripper", command=lambda: self.set_gripper(0)).pack(side=tk.LEFT, padx=4)

        right = ttk.LabelFrame(controls, text="Robot Status", padding=8)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.status_text = tk.Text(right, wrap=tk.WORD, height=28)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.configure(state=tk.DISABLED)

        if XArmAPI is None:
            self._append_status("xArm SDK not available. Install with: pip install xArm-Python-SDK")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _append_status(self, msg: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.status_text.configure(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"[{stamp}] {msg}\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state=tk.DISABLED)

    def _require_arm(self) -> bool:
        if self.arm is None:
            messagebox.showwarning("Not connected", "Connect to the robot first.")
            return False
        return True

    def connect(self) -> None:
        if XArmAPI is None:
            messagebox.showerror("Missing dependency", "xArm SDK is not installed.\nRun: pip install xArm-Python-SDK")
            return
        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Input error", "Please enter the robot IP address.")
            return
        try:
            self.arm = XArmAPI(ip)
            self.arm.connect()
            self.connection_label.config(text=f"Connected: {ip}", foreground="green")
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
            self._append_status(f"Connected to robot at {ip}")
            self._start_polling()
        except Exception as exc:  # noqa: BLE001
            self._append_status(f"Connection failed: {exc}")
            messagebox.showerror("Connection failed", str(exc))

    def disconnect(self) -> None:
        if self.arm is not None:
            try:
                self.polling = False
                self.arm.disconnect()
                self._append_status("Disconnected")
            except Exception as exc:  # noqa: BLE001
                self._append_status(f"Error while disconnecting: {exc}")
            self.arm = None
        self.connection_label.config(text="Not connected", foreground="red")
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)

    def enable_motion(self) -> None:
        if not self._require_arm():
            return
        self.arm.motion_enable(True)
        self._append_status("Motion enabled")

    def set_mode(self, mode: int) -> None:
        if not self._require_arm():
            return
        self.arm.set_mode(mode)
        self._append_status(f"Mode set to {mode}")

    def set_state(self, state: int) -> None:
        if not self._require_arm():
            return
        self.arm.set_state(state)
        self._append_status(f"State set to {state}")

    def clean_errors(self) -> None:
        if not self._require_arm():
            return
        self.arm.clean_error()
        self.arm.clean_warn()
        self._append_status("Warnings/errors cleaned")

    def emergency_stop(self) -> None:
        if not self._require_arm():
            return
        self.arm.emergency_stop()
        self._append_status("Emergency stop sent")

    def move_joints(self) -> None:
        if not self._require_arm():
            return
        try:
            joints = [float(v.get()) for v in self.joint_vars]
            speed = float(self.joint_speed.get())
            code = self.arm.set_servo_angle(angle=joints, speed=speed, wait=False, is_radian=False)
            self._append_status(f"Joint move command sent: {joints} (code={code})")
        except ValueError:
            messagebox.showwarning("Input error", "Joint values and speed must be numeric.")

    def move_cartesian(self) -> None:
        if not self._require_arm():
            return
        try:
            pose = [float(v.get()) for v in self.cart_vars]
            speed = float(self.cart_speed.get())
            code = self.arm.set_position(*pose, speed=speed, wait=False)
            self._append_status(f"Cartesian move sent: {pose} (code={code})")
        except ValueError:
            messagebox.showwarning("Input error", "Cartesian values and speed must be numeric.")

    def set_gripper(self, position: int) -> None:
        if not self._require_arm():
            return
        try:
            code = self.arm.set_gripper_position(position, wait=False)
            self._append_status(f"Gripper command {position} sent (code={code})")
        except Exception as exc:  # noqa: BLE001
            self._append_status(f"Gripper command failed: {exc}")

    def _start_polling(self) -> None:
        if self.polling:
            return
        self.polling = True
        self.status_thread = threading.Thread(target=self._poll_status, daemon=True)
        self.status_thread.start()

    def _poll_status(self) -> None:
        while self.polling:
            if self.arm is None:
                break
            try:
                state = self.arm.state
                error = self.arm.error_code
                warn = self.arm.warn_code
                self.root.after(0, self._append_status, f"state={state}, error={error}, warn={warn}")
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, self._append_status, f"Status polling error: {exc}")
            time.sleep(2)

    def on_close(self) -> None:
        self.disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = XArmControllerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
