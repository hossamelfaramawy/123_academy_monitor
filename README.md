# 123 Academy - Professional Exam Monitor System

This repository hosts the interactive, child-friendly skill assessments for **123 Academy** and houses the dispatcher engines that automate sending exam links to parents via WhatsApp.

---

## 🎮 Web Game Player (`index.html`)
The interactive game player at [index.html](file:///c:/Hossam/123/123Academy_MonitorSys_Repo/123_academy_monitor/index.html) parses student information from the URL parameters (e.g. `student_id`, `student_name`, `skill`) and generates a custom quiz:
* **Spaced Repetition**: Injects 3 questions from the active level and 2 random review questions from preceding levels.
* **Text-to-Speech (`audio-choice`)**: Pronounces English words out loud for vocabulary questions using the Web Speech API (at clear `0.75` speed) with vector cartoon illustrations instead of emojis.
* **Touch Drag & Drop (`drag-and-drop`)**: Allows kids to match uppercase and lowercase letter cards natively on tablets, phones, and PCs.
* **Make.com Webhook Integration**: Auto-submits results (`Passed` or `Needs Review`) back to your spreadsheet system.

---

## ⚙️ The Dispatcher Engines
We have three distinct engines designed for different deployment and budget requirements:

### 1. [twilio_cloud_dispatcher.py](file:///c:/Hossam/123/123Academy_MonitorSys_Repo/123_academy_monitor/twilio_cloud_dispatcher.py)
* **Purpose**: Production cloud automation.
* **How it works**: Runs automatically via **GitHub Actions** (on a schedule or cron job) using the Google Sheets API and the Twilio WhatsApp API.
* **Best for**: 100% hands-off automated weekly dispatching.

### 2. [twilio_local_dispatcher.py](file:///c:/Hossam/123/123Academy_MonitorSys_Repo/123_academy_monitor/twilio_local_dispatcher.py)
* **Purpose**: Local testing of Twilio messaging.
* **How it works**: Runs locally on your laptop, reading credentials and API secrets from a local `.env` file and dispatching messages via Twilio.
* **Best for**: Testing message layouts and verifying spreadsheet updates before pushing to the cloud.

### 3. [whatsapp_web_dispatcher.py](file:///c:/Hossam/123/123Academy_MonitorSys_Repo/123_academy_monitor/whatsapp_web_dispatcher.py)
* **Purpose**: Completely free local WhatsApp automation.
* **How it works**: Uses `webbrowser` and `pyautogui` to open WhatsApp Web tabs on your default browser, focuses the chat input, writes the prefilled exam invitation message, simulates the `Enter` key to send, and closes the tab.
* **Best for**: Unlimited, free messaging directly from your personal WhatsApp account without Twilio API fees. (Ensure you scan the WhatsApp Web QR code in your browser first).

## 📂 Curriculum Database Folders
All levels and question banks are organized in the `subjects/` directory:
* **English**: `subjects/english/eng_curriculum.json`
* **Arabic**: `subjects/arabic/ar_curriculum.json`
* **Math**: `subjects/math/math_curriculum.json`

---

## 📊 Google Sheet Grid Setup
The tracking sheet columns must be structured as follows:

`Student ID` | `Student Name` | `Parent Phone` | `Age Group` | `Math Level` | `Math Status` | `Arabic Level` | `Arabic Status` | `English Level` | `English Status` | `Last Sent Date`

### Status States:
* **`pending` (or empty)**: Ready to send.
* **`sent`**: Dispatched to the parent (set by scripts automatically).
* **`passed`**: Exam completed successfully (updated by Make.com webhook).
* **`needs_review`**: Exam completed but child failed (updated by Make.com webhook).

### Smart Level Resolving:
The scripts feature a smart name resolver. Sheet editors do not need to type database IDs like `english_3_s2`. You can type **"Letter B"**, **"حرف B"**, **"b"**, or **"B"** directly in the Level column, and the code will resolve it perfectly.

---

## 🧪 Dry-Run Mode (Testing Output)
If you want to test message generation and URL building without actually sending anything or opening browser windows:
1. Append `--dry-run` to your command:
   ```bash
   python twilio_local_dispatcher.py --dry-run
   python whatsapp_web_dispatcher.py --dry-run
   ```
2. Or set `DRY_RUN=true` in your environment (or `.env` file).

**What Dry-Run Mode does**:
* Prints all generated messages and links directly to the console.
* Saves all messages formatted to a local file: **`dry_run_output.txt`**.
* Bypasses Twilio API calls and PyAutoGUI browser automation.
* Does **not** modify your Google Sheet cells.

