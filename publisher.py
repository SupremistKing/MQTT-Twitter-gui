#!/usr/bin/env python3
"""
publisher.py — MQTT "Twitter-like" Publisher GUI
-------------------------------------------------
- Lets a user post a tweet to a hashtag (MQTT topic)
- Uses Tkinter for the GUI
- Uses paho-mqtt for MQTT client
- Publishes messages in the format: "<username>: <tweet_message>"

Default broker: test.mosquitto.org (public). You may replace with a local broker.
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
import queue
import time
import re

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

DEFAULT_BROKER = "test.mosquitto.org"
DEFAULT_PORT = 1883
TOPIC_PREFIX = "twitter/"  # final topic will be twitter/<hashtag>


def sanitize_hashtag(tag: str) -> str:
    """
    Normalize hashtag text:
      - remove leading '#' and whitespace
      - replace spaces with underscores
      - allow only letters, numbers, underscore, dash
    """
    tag = tag.strip()
    if tag.startswith("#"):
        tag = tag[1:]
    tag = re.sub(r"\s+", "_", tag)
    tag = re.sub(r"[^A-Za-z0-9_\-]", "", tag)
    return tag


class PublisherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MQTT Twitter — Publisher")
        self.geometry("520x420")
        self.resizable(False, False)

        # State
        self.client = None
        self.connected = False
        self.status_queue = queue.Queue()

        self._build_ui()
        self._init_mqtt()  # (no-op placeholder; kept for symmetry/future use)

        # Poll status queue to update GUI without blocking
        self.after(100, self._drain_status_queue)

    def _init_mqtt(self):
        """Placeholder for future MQTT setup (no-op)."""
        return

    def _build_ui(self):
        pad = {"padx": 12, "pady": 8}

        # Connection frame
        con_frame = ttk.LabelFrame(self, text="Broker Connection")
        con_frame.pack(fill="x", padx=12, pady=10)

        ttk.Label(con_frame, text="Broker:").grid(row=0, column=0, sticky="w", **pad)
        self.broker_var = tk.StringVar(value=DEFAULT_BROKER)
        ttk.Entry(con_frame, textvariable=self.broker_var, width=28).grid(row=0, column=1, **pad)

        ttk.Label(con_frame, text="Port:").grid(row=0, column=2, sticky="w", **pad)
        self.port_var = tk.IntVar(value=DEFAULT_PORT)
        ttk.Entry(con_frame, textvariable=self.port_var, width=8).grid(row=0, column=3, **pad)

        self.connect_btn = ttk.Button(con_frame, text="Connect", command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=4, **pad)

        self.status_lbl = ttk.Label(con_frame, text="Status: Disconnected", foreground="red")
        self.status_lbl.grid(row=1, column=0, columnspan=5, sticky="w", padx=12, pady=(0, 10))

        # Publish frame
        pub_frame = ttk.LabelFrame(self, text="Publish Tweet")
        pub_frame.pack(fill="x", padx=12, pady=10)

        ttk.Label(pub_frame, text="Username:").grid(row=0, column=0, sticky="w", **pad)
        self.username_var = tk.StringVar()
        ttk.Entry(pub_frame, textvariable=self.username_var, width=24).grid(row=0, column=1, **pad, sticky="w")

        ttk.Label(pub_frame, text="Hashtag:").grid(row=1, column=0, sticky="w", **pad)
        self.hashtag_var = tk.StringVar()
        ttk.Entry(pub_frame, textvariable=self.hashtag_var, width=24).grid(row=1, column=1, **pad, sticky="w")
        ttk.Label(pub_frame, text="(e.g., #iot or iot)").grid(row=1, column=2, sticky="w", padx=0)

        ttk.Label(pub_frame, text="Tweet:").grid(row=2, column=0, sticky="nw", **pad)
        self.tweet_text = tk.Text(pub_frame, height=5, width=45, wrap="word")
        self.tweet_text.grid(row=2, column=1, columnspan=2, **pad)

        self.publish_btn = ttk.Button(pub_frame, text="Publish Tweet", command=self._publish)
        self.publish_btn.grid(row=3, column=1, sticky="e", padx=12, pady=(0, 8))

        # Log frame
        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=8)

    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", time.strftime("[%H:%M:%S] ") + msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ---------- MQTT ----------
    def _toggle_connection(self):
        if not mqtt:
            messagebox.showerror("Missing dependency", "paho-mqtt is not installed.\n\npip install paho-mqtt")
            return
        if self.connected:
            try:
                self.client.disconnect()
            except Exception:
                pass
            self.connected = False
            self.connect_btn.config(text="Connect")
            self.status_lbl.config(text="Status: Disconnected", foreground="red")
            self._log("Disconnected from broker.")
        else:
            broker = self.broker_var.get().strip()
            port = int(self.port_var.get() or DEFAULT_PORT)
            self._connect_async(broker, port)

    def _connect_async(self, broker, port):
        self._log(f"Connecting to {broker}:{port} ...")
        self.status_lbl.config(text="Status: Connecting...", foreground="orange")

        def worker():
            try:
                self.client = mqtt.Client()
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.connect(broker, port, keepalive=60)
                # Start background network loop
                self.client.loop_start()
            except Exception as e:
                self.status_queue.put(("error", f"Connection failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.status_queue.put(("connected", "Connected to broker."))
        else:
            self.status_queue.put(("error", f"Failed to connect. Code: {reason_code}"))

    def _on_disconnect(self, client, userdata, reason_code, properties=None):
        self.status_queue.put(("disconnected", "Disconnected from broker."))

    def _drain_status_queue(self):
        try:
            while True:
                kind, msg = self.status_queue.get_nowait()
                if kind == "connected":
                    self.connected = True
                    self.connect_btn.config(text="Disconnect")
                    self.status_lbl.config(text="Status: Connected", foreground="green")
                    self._log(msg)
                elif kind == "disconnected":
                    self.connected = False
                    self.connect_btn.config(text="Connect")
                    self.status_lbl.config(text="Status: Disconnected", foreground="red")
                    self._log(msg)
                elif kind == "error":
                    self.connected = False
                    self.connect_btn.config(text="Connect")
                    self.status_lbl.config(text=f"Status: Error — see log", foreground="red")
                    self._log(msg)
        except queue.Empty:
            pass
        finally:
            self.after(150, self._drain_status_queue)

    def _publish(self):
        if not self.connected or not self.client:
            messagebox.showwarning("Not connected", "Please connect to a broker first.")
            return
        username = self.username_var.get().strip() or "anonymous"
        hashtag = sanitize_hashtag(self.hashtag_var.get())
        text = self.tweet_text.get("1.0", "end").strip()

        if not hashtag:
            messagebox.showwarning("Invalid hashtag", "Please enter a valid hashtag (e.g., #iot or iot).")
            return
        if not text:
            messagebox.showwarning("Empty tweet", "Please write something to publish.")
            return

        topic = f"{TOPIC_PREFIX}{hashtag}"
        payload = f"{username}: {text}"

        try:
            res = self.client.publish(topic, payload, qos=0, retain=False)
            if res.rc == 0:
                self._log(f"Published to '{topic}': {payload}")
                self.tweet_text.delete("1.0", "end")
            else:
                self._log(f"Publish failed (rc={res.rc})")
        except Exception as e:
            self._log(f"Publish error: {e}")


if __name__ == "__main__":
    app = PublisherApp()
    app.mainloop()
