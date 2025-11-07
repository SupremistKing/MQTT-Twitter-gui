#!/usr/bin/env python3
"""
subscriber.py — MQTT "Twitter-like" Subscriber GUI
--------------------------------------------------
- Lets a user subscribe/unsubscribe to hashtags (MQTT topics)
- Uses Tkinter for the GUI
- Shows incoming tweets live in a scrollable text area
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
TOPIC_PREFIX = "twitter/"  # expect topics like twitter/<hashtag>


def sanitize_hashtag(tag: str) -> str:
    tag = tag.strip()
    if tag.startswith("#"):
        tag = tag[1:]
    tag = re.sub(r"\s+", "_", tag)
    tag = re.sub(r"[^A-Za-z0-9_\-]", "", tag)
    return tag


class SubscriberApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MQTT Twitter — Subscriber")
        self.geometry("680x520")
        self.resizable(False, False)

        # State
        self.client = None
        self.connected = False
        self.msg_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.subscribed = set()

        self._build_ui()
        self._init_mqtt()  # (no-op placeholder)

        # Periodically drain queues to update UI
        self.after(100, self._drain_status_queue)
        self.after(100, self._drain_message_queue)

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

        # Subscription frame
        sub_frame = ttk.LabelFrame(self, text="Hashtag Subscription")
        sub_frame.pack(fill="x", padx=12, pady=10)

        ttk.Label(sub_frame, text="Hashtag:").grid(row=0, column=0, sticky="w", **pad)
        self.hashtag_var = tk.StringVar()
        ttk.Entry(sub_frame, textvariable=self.hashtag_var, width=28).grid(row=0, column=1, **pad)
        ttk.Label(sub_frame, text="(e.g., #iot or iot)").grid(row=0, column=2, sticky="w")

        ttk.Button(sub_frame, text="Subscribe", command=self._subscribe).grid(row=0, column=3, **pad)
        ttk.Button(sub_frame, text="Unsubscribe", command=self._unsubscribe).grid(row=0, column=4, **pad)

        # Subscribed list
        list_frame = ttk.LabelFrame(self, text="Subscribed Hashtags")
        list_frame.pack(fill="x", padx=12, pady=(0, 10))
        self.sub_list = tk.Listbox(list_frame, height=5)
        self.sub_list.pack(fill="x", padx=10, pady=8)

        # Messages frame
        msg_frame = ttk.LabelFrame(self, text="Live Tweet Feed")
        msg_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.msg_text = tk.Text(msg_frame, height=14, state="disabled", wrap="word")
        self.msg_text.pack(fill="both", expand=True, padx=10, pady=8)

    def _log_msg(self, line: str):
        self.msg_text.configure(state="normal")
        self.msg_text.insert("end", time.strftime("[%H:%M:%S] ") + line + "\n")
        self.msg_text.see("end")
        self.msg_text.configure(state="disabled")

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
            self._log_msg("Disconnected from broker.")
        else:
            broker = self.broker_var.get().strip()
            port = int(self.port_var.get() or DEFAULT_PORT)
            self._connect_async(broker, port)

    def _connect_async(self, broker, port):
        self.status_lbl.config(text="Status: Connecting...", foreground="orange")
        self._log_msg(f"Connecting to {broker}:{port} ...")

        def worker():
            try:
                self.client = mqtt.Client()
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.on_message = self._on_message
                self.client.connect(broker, port, keepalive=60)
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

    def _on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode("utf-8", errors="replace")
        except Exception:
            payload = "<binary payload>"
        topic = message.topic
        self.msg_queue.put(f"[{topic}] {payload}")

    def _drain_status_queue(self):
        try:
            while True:
                kind, msg = self.status_queue.get_nowait()
                if kind == "connected":
                    self.connected = True
                    self.connect_btn.config(text="Disconnect")
                    self.status_lbl.config(text="Status: Connected", foreground="green")
                    self._log_msg(msg)
                    # Re-subscribe to any previously subscribed topics on reconnect
                    for tag in list(self.subscribed):
                        self._subscribe_to_topic(tag)
                elif kind == "disconnected":
                    self.connected = False
                    self.connect_btn.config(text="Connect")
                    self.status_lbl.config(text="Status: Disconnected", foreground="red")
                    self._log_msg(msg)
                elif kind == "error":
                    self.connected = False
                    self.connect_btn.config(text="Connect")
                    self.status_lbl.config(text=f"Status: Error — see feed", foreground="red")
                    self._log_msg(msg)
        except queue.Empty:
            pass
        finally:
            self.after(150, self._drain_status_queue)

    def _drain_message_queue(self):
        try:
            while True:
                line = self.msg_queue.get_nowait()
                self._log_msg(line)
        except queue.Empty:
            pass
        finally:
            self.after(120, self._drain_message_queue)

    # ---------- Subscribe/Unsubscribe ----------
    def _subscribe(self):
        tag = sanitize_hashtag(self.hashtag_var.get())
        if not tag:
            messagebox.showwarning("Invalid hashtag", "Please enter a valid hashtag (e.g., #iot or iot).")
            return
        if tag in self.subscribed:
            messagebox.showinfo("Already subscribed", f"You're already following #{tag}.")
            return
        self.subscribed.add(tag)
        self.sub_list.insert("end", f"#{tag}")
        self._subscribe_to_topic(tag)

    def _subscribe_to_topic(self, tag: str):
        if not self.connected or not self.client:
            self._log_msg(f"(queued) Will subscribe to #{tag} when connected.")
            return
        topic = f"{TOPIC_PREFIX}{tag}"
        try:
            self.client.subscribe(topic, qos=0)
            self._log_msg(f"Subscribed to '{topic}'")
        except Exception as e:
            self._log_msg(f"Subscribe error for '{topic}': {e}")

    def _unsubscribe(self):
        # If an item is selected, remove that. Otherwise use the entry box.
        selection = self.sub_list.curselection()
        if selection:
            label = self.sub_list.get(selection[0])
            tag = label.lstrip("#")
        else:
            tag = sanitize_hashtag(self.hashtag_var.get())

        if not tag or tag not in self.subscribed:
            messagebox.showinfo("Not subscribed", "Select a hashtag in the list or type one you're subscribed to.")
            return

        self.subscribed.remove(tag)
        # remove from listbox
        for i in range(self.sub_list.size()):
            if self.sub_list.get(i).lstrip("#") == tag:
                self.sub_list.delete(i)
                break

        if self.connected and self.client:
            topic = f"{TOPIC_PREFIX}{tag}"
            try:
                self.client.unsubscribe(topic)
                self._log_msg(f"Unsubscribed from '{topic}'")
            except Exception as e:
                self._log_msg(f"Unsubscribe error for '{topic}': {e}")
        else:
            self._log_msg(f"(queued removal) #{tag} will not be re-subscribed on connect.")

if __name__ == "__main__":
    app = SubscriberApp()
    app.mainloop()
