
# Assignment 2 — MQTT Twitter (Publisher & Subscriber)

## 👨‍💻 Student Info
**Name:** Nikhil  
**Assignment:** 2  
**Course:** Distributed Systems — MQTT Twitter Simulation  

---

## 🎯 Objective
This project demonstrates a Twitter-like distributed publish–subscribe system using the **MQTT protocol** and **Tkinter GUI**.  
Users can post tweets under hashtags, and subscribers receive them in real time.

---

## 🧩 Files
| File | Description |
|------|--------------|
| `publisher.py` | GUI for posting tweets (publishes to MQTT topics). |
| `subscriber.py` | GUI for subscribing to hashtags and viewing tweets live. |
| `requirements.txt` | Lists required packages. |
| `screenshots/` | Contains demo screenshots for submission. |

---

## 🚀 How to Run
### Step 1. Setup
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2. Run the Publisher
```bash
python publisher.py
```
Then click **Connect**, fill in username, hashtag, and message, and click **Publish Tweet**.

### Step 3. Run the Subscriber
In another PowerShell window:
```bash
.\.venv\Scripts\activate
python subscriber.py
```
Then click **Connect**, enter the same hashtag, and click **Subscribe**.  
You’ll see the published tweet instantly.

---

## ⚙️ Broker Configuration
- **Broker:** `test.mosquitto.org` (public MQTT broker)
- **Port:** `1883`
- Topics are automatically prefixed as `twitter/<hashtag>`.  
  Example: `#iot` → `twitter/iot`

---

## 📸 Screenshots
Include:
1. `image1_publisher_subscriber.png` → both GUIs running, messages flowing  
2. `image2_tkinter_gui.png` → Tkinter GUI layout  

Place them in the `screenshots/` folder.

---

## 🧾 Submission
1. Upload this folder to **GitHub** as:  
   ```
   MQTT-Twitter
   ```
2. Push your code:
   ```bash
   git init
   git add .
   git commit -m "Assignment 2 - MQTT Twitter"
   git branch -M main
   git remote add origin https://github.com/<your-username>/MQTT-Twitter.git
   git push -u origin main
   ```
3. Submit your **GitHub repository link** and your **screenshots** on the assignment portal.

---

## ✅ Learning Outcomes
- Implemented an MQTT Pub–Sub model  
- Built GUI-based publisher/subscriber apps  
- Demonstrated distributed communication in real time  
