import RPi.GPIO as GPIO
from picamera2 import Picamera2
from libcamera import controls, Transform
import tkinter as tk
from tkinter import font
import threading
import time
import yagmail
from imapclient import IMAPClient
import email
from email.header import decode_header
from datetime import datetime
from pathlib import Path
import subprocess

# --- HARDWARE CONFIGURATION ---
SENSOR_PIN = 16
PUMP_PIN = 20
LED_PIN1 = 5
LED_PIN2 = 12
LED_PIN3 = 13

WATERING_INTERVAL = 30
VIDEO_FPS = 2
SAVE_DIR = "/home/pi/timelapse"
TIMELAPSE_NAME = "timelapse.mp4"

# --- GPIO SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.HIGH) # OFF
GPIO.setup(LED_PIN1, GPIO.OUT)
GPIO.output(LED_PIN1, GPIO.LOW)
GPIO.setup(LED_PIN2, GPIO.OUT)
GPIO.output(LED_PIN2, GPIO.LOW)
GPIO.setup(LED_PIN3, GPIO.OUT)
GPIO.output(LED_PIN3, GPIO.LOW)
print("GPIO Initialised")

# --- CAMERA SETUP --- 
camera = Picamera2()
config = camera.create_still_configuration(transform=Transform(hflip=True, vflip=True))
camera.configure(config)
# If more control of camera is required, uncomment this section
camera.set_controls({
	"AfMode": controls.AfModeEnum.Manual,
	"LensPosition": 6.75
})
camera.start()

# --- EMAIL SETUP ---
image_path = ""
password = "nvnm kmbw zlck zffs"

IMAP_HOST = "imap.gmail.com"
USERNAME = "mpimailserve@gmail.com"

yag = yagmail.SMTP("mpimailserve@gmail.com", password)

# --- GLOBAL FLAGS ---
stop_watering = threading.Event()
stop_timelapse = threading.Event()
stop_imap_listener = threading.Event()
auto_watering_thread = None
timelapse_thread = None
imap_listener_thread = None
isLightOn = False
isRecording = False
current_ffmpeg_proc = None

# --- COLORS & STYLES ---
COLOR_BG = "#2C3E50"		# Dark Blue-Grey
COLOR_PANEL = "#34495E"		# Lighter Blue-Grey
COLOR_TEXT = "#ECF0F1"		# Off-White
COLOR_ACCENT = "#27AE60"	# Green
COLOR_WARN = "#E74C3C"		# Red
COLOR_BTN_TXT = "#FFFFFF"

# --- CALLBACKS ---


# --- LOGIC FUNCTIONS ---
def interruptible_sleep(stop_flag, total_duration, interval=0.1):
	elapsed = 0
	while elapsed < total_duration:
		start_time = time.time()
		if stop_flag.is_set():
			return False
		time.sleep(interval)
		elapsed += interval
	return True

def update_status(message):
	"""Updates the status label at the bottom of the screen"""
	status_label.config(text=f"Status: {message}")

# --- Watering Logic ---
def auto_watering_loop():
	isDry = False
	update_status("Auto-Watering Active")
	try:
		while not stop_watering.is_set():
			# Logic kept from original code
			if GPIO.input(SENSOR_PIN) == GPIO.HIGH and isDry == False:
				isDry = True
			elif GPIO.input(SENSOR_PIN) == GPIO.LOW and isDry == True:
				isDry = False
				update_status("Watering Done.")
			
			if isDry == True:
				update_status("Plant is dry! Watering...")
				GPIO.output(PUMP_PIN, GPIO.LOW)
				interruptible_sleep(stop_watering, 1)
				GPIO.output(PUMP_PIN, GPIO.HIGH)
				
			
			interruptible_sleep(stop_watering, WATERING_INTERVAL)
	finally:
		GPIO.output(PUMP_PIN, GPIO.HIGH)
		update_status("Auto-Watering Stopped")

def toggle_auto_watering():
	global auto_watering_thread
	
	if auto_watering_var.get():
		waterButton.config(state="disabled", bg="#7f8c8d") # Gray out manual button
		stop_watering.clear()
		if auto_watering_thread is None or not auto_watering_thread.is_alive():
			auto_watering_thread = threading.Thread(target=auto_watering_loop, daemon=False)
			auto_watering_thread.start()
			autoWaterCheck.config(selectcolor=COLOR_ACCENT) # Green check
	else:
		stop_watering.set()
		waterButton.config(state="normal", bg=COLOR_ACCENT)
		update_status("Manual Mode")
		autoWaterCheck.config(selectcolor=COLOR_PANEL)

def on_waterButton_press(event):
	if waterButton.cget("state") != "disabled":
		GPIO.output(PUMP_PIN, GPIO.LOW)
		waterButton.config(bg="#2ECC71") # Lighter green when pressed
		update_status("Pump Active")

def on_waterButton_release(event):
	if waterButton.cget("state") != "disabled":
		GPIO.output(PUMP_PIN, GPIO.HIGH)
		waterButton.config(bg=COLOR_ACCENT) # Back to normal green
		update_status("Pump Stopped")

def toggle_LED():
	global isLightOn
	if not isLightOn:
		# ~ GPIO.output(LED_PIN1, GPIO.LOW)
		GPIO.output(LED_PIN2, GPIO.HIGH)
		# ~ GPIO.output(LED_PIN3, GPIO.HIGH)
		ledButton.config(text="Turn LEDs OFF", bg="#F1C40F", fg="#2C3E50") # Yellow
		isLightOn = True
	else:
		# ~ GPIO.output(LED_PIN1, GPIO.LOW)
		GPIO.output(LED_PIN2, GPIO.LOW)
		# ~ GPIO.output(LED_PIN3, GPIO.LOW)
		ledButton.config(text="Turn LEDs ON", bg=COLOR_PANEL, fg=COLOR_TEXT)
		isLightOn = False

# --- Camera Logic ---
def capture_photo(filename=""):
	global SAVE_DIR
	
	if filename == "":
		filename = f"{SAVE_DIR}/image.jpg"
	
	with camera.captured_request() as request:
		try:
			request.save("main", filename)
		except Exception as e:
			print("Error with code: ", e)
		else:
			update_status("Photo Captured")
	return filename

def timelapse_loop(stop_flag, capture_interval):
	global SAVE_DIR
	try:
		count = 0
		while not stop_flag.is_set():
			lapTime = time.time()
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			filename = f"{SAVE_DIR}/image_{timestamp}.jpg"
			
			capture_photo(filename)
			
			print(f"[{count}] Captured {filename}")
			interruptible_sleep(stop_flag, (capture_interval - (time.time() - lapTime)))	# subtract processing time from interval
			
	finally:
		print("Timelapse stopped")

def toggle_timelapse():
	global isRecording, timelapse_thread
	
	try:
		capture_interval = int(captureIntervalEntry.get())
	except ValueError:
		update_status("Error: Invalid Interval")
		return

	if not isRecording:
		stop_timelapse.clear()
		if timelapse_thread is None or not timelapse_thread.is_alive():
			timelapse_thread = threading.Thread(target=timelapse_loop, args=(stop_timelapse, capture_interval), daemon=False)
			timelapse_thread.start()
			
			isRecording = True
			recordingButton.config(text="Stop Recording", bg=COLOR_WARN, activebackground="#c0392b")
			update_status("Timelapse Recording...")
		
	else:
		stop_timelapse.set()
		recordingButton.config(text="Start Recording", bg=COLOR_PANEL, activebackground="#7f8c8d")
		isRecording = False
		update_status("Recording Stopped")

def render_timelapse(date_start: str, date_end: str):
	start_ts = f"{date_start}_000000"
	end_ts   = f"{date_end}_235959"

	update_status("Rendering video...")

	fps = VIDEO_FPS
	directory = Path(SAVE_DIR)
	file_list_path = directory / "file_list.txt"

	# Extract timestamp part from file name "image_YYYYMMDD_HHMMSS.jpg"
	def extract_timestamp(path: Path):
		stem = path.stem
		return stem.split("_", 1)[1]

	# Get all images and filter by timestamps
	all_images = sorted(directory.glob("image_*.jpg"))

	selected = [
		img for img in all_images
		if start_ts <= extract_timestamp(img) <= end_ts
	]

	if not selected:
		print("No images found in the given date range.")
		return
	# Calculate & write how many times each image should be duplicated in the concat list
	frames_per_image = max(1, 24 // VIDEO_FPS)

	with open(file_list_path, "w") as f:
		for img in selected:
			for _ in range(frames_per_image):
				f.write(f"file '{img}'\n")

	output_video = directory / f"{TIMELAPSE_NAME}"

	ffmpeg_cmd = [
		"nice", "-n", "10",
		"ffmpeg",
		"-y",
		"-f", "concat",
		"-safe", "0",
		"-i", str(file_list_path),
		"-vf", f"scale=960:-1,fps=24",
		"-vcodec", "libx264",
		"-threads", "2",
		"-pix_fmt", "yuv420p",
		str(output_video)
	]

	print("Starting FFmpeg render...")

	global current_ffmpeg_proc
	current_ffmpeg_proc = subprocess.Popen(
		ffmpeg_cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True
	)

	# Monitor thread to notify when done
	def ffmpeg_done(proc: subprocess.Popen):
		for line in proc.stdout:
			print(line, end="")
		proc.wait()
		print("Render finished!")
		update_status("Render complete.")

	threading.Thread(target=ffmpeg_done, args=(current_ffmpeg_proc,), daemon=True).start()

def render_button_callback():
	start_date = dateStart_var.get()
	end_date = dateEnd_var.get()
	render_timelapse(start_date, end_date)

# --- EMAIL WORKER ---
def email_ondemand_photo():
	image_path = capture_photo()
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	
	yag.send(
		to='purvesm@student.douglascollege.ca',
		subject="Requested Photo",
		contents = f"Photo taken at {timestamp}",
		attachments = image_path
	)

def email_ondemand_video():
	video_path = "/home/pi/timelapse/timelapse.mp4"
	
	yag.send(
		to='purvesm@student.douglascollege.ca',
		subject="Requested Video",
		contents = "",
		attachments = video_path
	)

def parse_command(command: str):
	print(f"[CMD] {command}")

	if command == "PING":
		print("PONG!")
	elif command == "PHOTO":
		email_ondemand_photo()
	elif command == "VIDEO":
		email_ondemand_video()
	elif command.startswith("RUN:"):
		print(f"Would run function: {command[4:]}")
	else:
		print("Unknown command")

def process_unseen_messages(server):
	print("Processing")

	messages = server.search(["UNSEEN"])
	print("Startuing Query")
	for msgid in messages:
		raw = server.fetch([msgid], ["RFC822"])[msgid][b"RFC822"]
		message = email.message_from_bytes(raw)
		print("message variable assigned")
		# Decode subject safely
		dh = decode_header(message.get("Subject"))
		subject_bytes, subj_encoding = dh[0]
		subject = subject_bytes.decode(subj_encoding or "utf-8") if isinstance(subject_bytes, bytes) else subject_bytes

		print(f"Processing email: {subject}")
		parse_command(subject)

def imap_idle_update_loop(stop_flag):
	while not stop_flag.is_set():
		try:
			print("[IMAP] Connecting…")
			with IMAPClient(IMAP_HOST, use_uid=True, ssl=True) as server:

				print("[IMAP] Logging in…")
				server.login(USERNAME, password)

				print("[IMAP] Selecting INBOX…")
				server.select_folder("INBOX")

				while not stop_flag.is_set():
					start_time = time.time()
					print("[IMAP] Entering IDLE…")
					# Start IDLE
					server.idle()
					try:
						while not stop_flag.is_set() and (time.time() - start_time) < 120:
							print("[IMAP] IDLE Check...")
							responses = server.idle_check(timeout=15)
							
							if responses:
								print("[IMAP] Event received:", responses)
								server.idle_done()
								process_unseen_messages(server)
					finally:
						try:
							server.idle_done()
						except Exception:
							pass
		except Exception as e:
			print(f"[IDLE] Error: {e}. Reconnecting in 5 seconds…")
			time.sleep(5)

def start_imap_listener():
	global imap_listener_thread
	
	stop_imap_listener.clear()
	if imap_listener_thread is None or not imap_listener_thread.is_alive():
			imap_listener_thread = threading.Thread(target=imap_idle_update_loop, args=(stop_imap_listener,), daemon=True)
			imap_listener_thread.start()

# Uncomment if you wish to run IMAP/IDLE
# ~ start_imap_listener()

def on_close():
	stop_watering.set()
	stop_timelapse.set()
	if auto_watering_thread is not None:
		auto_watering_thread.join()
	if timelapse_thread is not None:
		timelapse_thread.join()
	camera.stop()
	try:
		GPIO.cleanup()
	except:
		pass
	
	update_status("Waiting on IMAP/IDLE to finish...")
	time.sleep(0.5)
	stop_imap_listener.set()
	if imap_listener_thread is not None:
		imap_listener_thread.join()
	mainwindow.destroy()

# --- GUI SETUP ---
mainwindow = tk.Tk()
mainwindow.title("PPWS - Smart Garden")
mainwindow.geometry("800x480") # Common Pi Screen size
mainwindow.configure(bg=COLOR_BG)

# Custom Fonts
header_font = font.Font(family="Helvetica", size=16, weight="bold")
btn_font = font.Font(family="Helvetica", size=12)

# HEADER
header_frame = tk.Frame(mainwindow, bg=COLOR_BG)
header_frame.pack(fill="x", pady=15)
title_label = tk.Label(header_frame, text="🌱 Pi Plant Watering System", font=("Helvetica", 24, "bold"), bg=COLOR_BG, fg="#2ECC71")
title_label.pack()

# MAIN CONTENT CONTAINER
content_frame = tk.Frame(mainwindow, bg=COLOR_BG)
content_frame.pack(expand=True, fill="both", padx=20, pady=10)

# --- LEFT PANEL (PLANT CARE) ---
left_panel = tk.LabelFrame(content_frame, text="  Plant Control  ", font=header_font, bg=COLOR_BG, fg=COLOR_TEXT, bd=2, relief="groove")
left_panel.pack(side="left", fill="both", expand=True, padx=10)

# Auto Water Switch
auto_watering_var = tk.BooleanVar(value=False)
autoWaterCheck = tk.Checkbutton(
	left_panel, 
	text="Enable Auto-Watering", 
	variable=auto_watering_var, 
	command=toggle_auto_watering,
	bg=COLOR_BG, fg=COLOR_TEXT, selectcolor=COLOR_PANEL, activebackground=COLOR_BG, activeforeground=COLOR_TEXT,
	font=btn_font
)
autoWaterCheck.pack(pady=20)

# Manual Water Button (Big Green Button)
waterButton = tk.Button(
	left_panel, text="💧 HOLD TO WATER", 
	font=("Helvetica", 14, "bold"),
	bg=COLOR_ACCENT, fg="white",
	activebackground="#2ECC71", activeforeground="white",
	relief="flat", cursor="hand2", height=2
)
waterButton.pack(fill="x", padx=30, pady=10)
waterButton.bind("<ButtonPress-1>", on_waterButton_press)
waterButton.bind("<ButtonRelease-1>", on_waterButton_release)

# LED Toggle
ledButton = tk.Button(
	left_panel, text="Turn LEDs ON",
	font=btn_font,
	bg=COLOR_PANEL, fg=COLOR_TEXT,
	activebackground="#95a5a6", activeforeground="black",
	relief="flat", command=toggle_LED
)
ledButton.pack(fill="x", padx=30, pady=10)

# --- RIGHT PANEL (TIMELAPSE) ---
right_panel = tk.LabelFrame(content_frame, text="  Camera & Timelapse  ", font=header_font, bg=COLOR_BG, fg=COLOR_TEXT, bd=2, relief="groove")
right_panel.pack(side="right", fill="both", expand=True, padx=10)

# Interval Input
interval_frame = tk.Frame(right_panel, bg=COLOR_BG)
interval_frame.pack(pady=20)
tk.Label(interval_frame, text="Interval (sec):", bg=COLOR_BG, fg=COLOR_TEXT, font=btn_font).pack(side="left")
captureInterval_var = tk.IntVar(value=30)
captureIntervalEntry = tk.Entry(interval_frame, textvariable=captureInterval_var, width=5, font=btn_font, justify="center")
captureIntervalEntry.pack(side="left", padx=10)

# Record Button
recordingButton = tk.Button(
	right_panel, text="Start Recording",
	font=btn_font,
	bg=COLOR_PANEL, fg=COLOR_TEXT,
	activebackground="#95a5a6", activeforeground="black",
	relief="flat", command=toggle_timelapse
)
recordingButton.pack(fill="x", padx=30, pady=5)

# Date Range Inputs
date_frame = tk.Frame(right_panel, bg=COLOR_BG)
date_frame.pack(pady=10)

tk.Label(date_frame, text="Start Date (YYYYMMDD):", bg=COLOR_BG, fg=COLOR_TEXT, font=btn_font).grid(row=0, column=0, sticky="e")
dateStart_var = tk.StringVar(value="20251114")
dateStartEntry = tk.Entry(date_frame, textvariable=dateStart_var, width=10, font=btn_font)
dateStartEntry.grid(row=0, column=1, padx=5)

tk.Label(date_frame, text="End Date (YYYYMMDD):", bg=COLOR_BG, fg=COLOR_TEXT, font=btn_font).grid(row=1, column=0, sticky="e")
dateEnd_var = tk.StringVar(value="20251120")
dateEndEntry = tk.Entry(date_frame, textvariable=dateEnd_var, width=10, font=btn_font)
dateEndEntry.grid(row=1, column=1, padx=5)

# Render Button
renderButton = tk.Button(
	right_panel, text="Render Video",
	font=btn_font,
	bg=COLOR_PANEL, fg=COLOR_TEXT,
	activebackground="#95a5a6", activeforeground="black",
	relief="flat", command=render_button_callback  # <--- updated
)
renderButton.pack(fill="x", padx=30, pady=5)
# Snap Photo
capturePhotoButton = tk.Button(
	right_panel, text="📷 Snap Photo",
	font=btn_font,
	bg="#3498DB", fg="white",
	activebackground="#2980B9", activeforeground="white",
	relief="flat", command=capture_photo
)
capturePhotoButton.pack(fill="x", padx=30, pady=(20, 5))

# --- FOOTER ---
footer_frame = tk.Frame(mainwindow, bg=COLOR_BG)
footer_frame.pack(fill="x", pady=10)

status_label = tk.Label(footer_frame, text="Status: Ready", bd=1, relief="sunken", anchor="w", bg="#22313F", fg="#BDC3C7", font=("Courier", 10))
status_label.pack(fill="x", padx=10, pady=(0, 10))

quitButton = tk.Button(
	footer_frame, text="EXIT SYSTEM",
	font=("Helvetica", 10, "bold"),
	bg=COLOR_WARN, fg="white",
	relief="flat", command=on_close
)
quitButton.pack(side="bottom", pady=5)

mainwindow.protocol("WM_DELETE_WINDOW", on_close)

# --- LAUNCH ---
try:
	mainwindow.mainloop()
except KeyboardInterrupt:
	on_close()
