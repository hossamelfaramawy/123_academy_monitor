import os
import json
import datetime
import sys
import time
import webbrowser
from urllib.parse import quote_plus
import gspread
from google.oauth2.service_account import Credentials

# Import pyautogui to automate keystrokes
try:
    import pyautogui
except ImportError:
    print("❌ Error: The 'pyautogui' package is not installed.")
    print("Please run: python -m pip install pyautogui")
    sys.exit(1)

# Reconfigure stdout for Windows terminal emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def load_dotenv():
    """Manually parse .env file to load variables into os.environ without dependencies."""
    env_path = ".env"
    if os.path.exists(env_path):
        print(f"📝 Loading local credentials from '{env_path}'...")
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        current_key = None
        current_value = []
        
        for line in lines:
            line_strip = line.strip()
            
            # If we are not currently collecting a multi-line value
            if not current_key:
                if not line_strip or line_strip.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    
                    # Check if it starts a JSON block
                    if val.startswith("{") and not val.endswith("}"):
                        current_key = key
                        current_value = [val]
                    else:
                        # Strip whitespace and surrounding quotes
                        os.environ[key] = val.strip("'").strip('"')
            else:
                # We are collecting a multi-line value
                current_value.append(line.rstrip())
                if line_strip == "}" or line_strip.endswith("}"):
                    os.environ[current_key] = "\n".join(current_value)
                    current_key = None
                    current_value = []
    else:
        print("⚠️ Warning: No '.env' file found. Running with system environment variables.")

def resolve_skill_id(sheet_val, subject, curriculum):
    """Resolves a friendly sheet value like 'Letter B', 'B', 'b' to curriculum ID like 'english_3_s2'."""
    val_clean = sheet_val.strip().lower()
    if not val_clean:
        return None
        
    # 1. Direct ID match
    if val_clean in curriculum:
        return val_clean
        
    # 2. Direct title match (case insensitive)
    for skill_id, skill in curriculum.items():
        if skill.get("subject") == subject:
            if val_clean == skill.get("title_en", "").strip().lower():
                return skill_id
            if val_clean == skill.get("title_ar", "").strip().lower():
                return skill_id
                
    # 3. Clean up prefix like "letter ", "حرف " to match just the core value (e.g. "b", "c")
    core_val = val_clean.replace("letter", "").replace("حرف", "").strip()
    
    # 4. Try matching the core value
    for skill_id, skill in curriculum.items():
        if skill.get("subject") == subject:
            title_en_core = skill.get("title_en", "").strip().lower().replace("letter", "").replace("حرف", "").strip()
            title_ar_core = skill.get("title_ar", "").strip().lower().replace("letter", "").replace("حرف", "").strip()
            if core_val == title_en_core or core_val == title_ar_core:
                return skill_id
                
    return None

def main():
    load_dotenv()
    
    # Check if running in dry-run mode
    dry_run = "--dry-run" in sys.argv or os.environ.get("DRY_RUN", "").lower() == "true"
    dry_run_messages = []
    
    if dry_run:
        print("🧪 RUNNING IN DRY-RUN (TEST) MODE - Browser will not be opened, Google Sheet will not be modified.")
    else:
        print("🚀 Starting 123 Academy WhatsApp Web Browser Dispatcher...")
        print("📢 IMPORTANT: Make sure you have scanned your WhatsApp Web QR code in your default browser first!")

    # 1. Load Curriculum Data from subject subdirectories
    curriculum = {}
    subject_files = {
        "math": "subjects/math/math_curriculum.json",
        "arabic": "subjects/arabic/ar_curriculum.json",
        "english": "subjects/english/eng_curriculum.json"
    }
    
    for sub, path in subject_files.items():
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    sub_data = json.load(f)
                    curriculum.update(sub_data)
                print(f"  📖 Loaded {len(sub_data)} skills from '{path}'")
            except Exception as e:
                print(f"  ⚠️ Error loading '{path}': {e}")
                return
        else:
            print(f"  ℹ️ Subject curriculum '{path}' not found (skipping)")
            
    print(f"📖 Combined total: Loaded {len(curriculum)} skills across all subjects.")

    # 2. Get Environment Variables
    pages_base = os.environ.get("PAGES_BASE_URL")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Sheet1")
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    # Display configuration
    print("\n📋 Current Configuration:")
    print(f"  - PAGES_BASE_URL: '{pages_base}'")
    print(f"  - GOOGLE_SHEET_ID: '{sheet_id[:6]}...'" if sheet_id else "  - GOOGLE_SHEET_ID: None")
    print(f"  - GOOGLE_SHEET_NAME: '{sheet_name}'")
    print(f"  - GOOGLE_SERVICE_ACCOUNT_JSON: {'[LOADED]' if service_account_json else '[MISSING]'}\n")

    # Validate essential environment variables
    missing_vars = []
    if not pages_base: missing_vars.append("PAGES_BASE_URL")
    if not sheet_id: missing_vars.append("GOOGLE_SHEET_ID")
    if not service_account_json: missing_vars.append("GOOGLE_SERVICE_ACCOUNT_JSON")

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your '.env' file. Stopping execution.")
        return

    # Make sure base URL ends with a slash
    if not pages_base.endswith("/"):
        pages_base += "/"

    # 3. Authenticate with Google Sheets API
    try:
        clean_json_val = service_account_json.strip()
        if clean_json_val.endswith(".json") and os.path.exists(clean_json_val):
            print(f"📂 Loading Google credentials from local key file: '{clean_json_val}'")
            with open(clean_json_val, "r", encoding="utf-8") as f:
                creds_dict = json.load(f)
        else:
            try:
                creds_dict = json.loads(service_account_json)
            except json.JSONDecodeError as je:
                try:
                    fixed_json = service_account_json.replace("'", '"')
                    creds_dict = json.loads(fixed_json)
                except Exception:
                    print(f"❌ Google Credentials JSON Parse Error: {je}")
                    raise je

        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        # Open sheet
        sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)
        print(f"✅ Successfully opened Google Sheet: '{sheet.title}'")
    except Exception as e:
        print(f"❌ Google Sheets Auth / Connection failed: {e}")
        return

    # 4. Read Spreadsheet and Header Mapping
    all_records = sheet.get_all_values()
    if len(all_records) < 2:
        print("⚠️ Spreadsheet is empty or only has headers. No students to notify.")
        return

    headers = [h.strip().lower() for h in all_records[0]]

    # Map general column headers
    try:
        col_student_id = headers.index("student id")
        col_student_name = headers.index("student name")
        col_parent_phone = headers.index("parent phone")
        col_age_group = headers.index("age group")
        col_last_sent = headers.index("last sent date")
    except ValueError as e:
        print(f"❌ Header structure error: {e}")
        print("Ensure general columns exist: 'Student ID', 'Student Name', 'Parent Phone', 'Age Group', 'Last Sent Date'")
        return

    # Map the subject Level and Status columns to their 0-indexed column coordinates
    subjects = ["math", "arabic", "english"]
    subject_cols = {}
    for sub in subjects:
        try:
            level_idx = headers.index(f"{sub} level")
            status_idx = headers.index(f"{sub} status")
            subject_cols[sub] = {
                "level_idx": level_idx,
                "status_idx": status_idx
            }
        except ValueError as e:
            print(f"❌ Header structure error: {e}")
            print(f"Ensure level & status columns exist: '{sub.capitalize()} Level', '{sub.capitalize()} Status'")
            return

    # 5. Iterate through student rows and send exams
    sent_count = 0
    fail_count = 0
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row_idx, row in enumerate(all_records[1:], start=2):
        if len(row) <= max(col_student_id, col_student_name, col_parent_phone, col_age_group):
            continue

        student_id = row[col_student_id].strip()
        student_name = row[col_student_name].strip()
        parent_phone = row[col_parent_phone].strip()
        age_group_str = row[col_age_group].strip()

        if not student_id or not parent_phone:
            continue

        try:
            age_group = int(age_group_str)
        except ValueError:
            age_group = 3  # default to age group 3 if missing or invalid

        # Find the pending skill for each subject using level & status pairs
        pending_skills = []

        for sub in subjects:
            level_idx = subject_cols[sub]["level_idx"]
            status_idx = subject_cols[sub]["status_idx"]
            
            skill_id = ""
            if level_idx < len(row):
                skill_id = row[level_idx].strip()
                
            status = ""
            if status_idx < len(row):
                status = row[status_idx].strip().lower()

            # If Level is empty, there is no exam assigned for this subject yet
            if not skill_id:
                continue

            # Resolve friendly name/ID to actual skill_id from curriculum (ignoring age check)
            resolved_id = resolve_skill_id(skill_id, sub, curriculum)

            # If status is not "passed" (meaning it is pending, sent, needs_review, or empty)
            if status != "passed":
                if resolved_id:
                    pending_skills.append({
                        "subject": sub,
                        "level_idx": level_idx,
                        "status_idx": status_idx,
                        "skill_id": resolved_id,
                        "curriculum_data": curriculum[resolved_id]
                    })
                else:
                    print(f"  ⚠️ Warning: Could not resolve Level name '{skill_id}' to a valid skill ID in curriculum.json")

        if not pending_skills:
            continue

        print(f"\n📧 Preparing message for: '{student_name}' (ID: {student_id}, Age: {age_group})")

        # 6. Construct combined WhatsApp message
        message_lines = []
        message_lines.append(f"مرحباً يا ولي أمر {student_name} 👋")
        message_lines.append("")
        message_lines.append("حان وقت الألعاب التعليمية التفاعلية لهذا الأسبوع لطفلكم المتميز في أكاديمية 123! 🌟")
        message_lines.append("الرجاء من البطل الصغير حل التحديات التالية:")
        message_lines.append("")

        subject_metadata = {
            "math": {"emoji": "➕", "name": "الرياضيات (Math)", "title_key": "title_ar"},
            "arabic": {"emoji": "✏️", "name": "اللغة العربية (Arabic)", "title_key": "title_ar"},
            "english": {"emoji": "🔤", "name": "اللغة الإنجليزية (English)", "title_key": "title_en"}
        }

        for skill in pending_skills:
            sub = skill["subject"]
            meta = subject_metadata[sub]
            skill_id = skill["skill_id"]
            
            title_key = meta["title_key"]
            skill_title = skill["curriculum_data"].get(title_key, skill_id)
            
            escaped_name = quote_plus(student_name)
            exam_url = f"{pages_base}?student_id={student_id}&skill={skill_id}&student_name={escaped_name}"
            
            message_lines.append(f"{meta['emoji']} {meta['name']}: {skill_title}")
            message_lines.append(f"رابط اللعبة: {exam_url}")
            message_lines.append("")

        message_lines.append("بالتوفيق للبطل! 🏆🎈")
        message_body = "\n".join(message_lines)

        # Standardize phone number for WhatsApp Web URL (digits only, no '+' sign)
        clean_phone = parent_phone.replace(" ", "").replace("-", "").replace("+", "")
        if clean_phone.startswith("00"):
            clean_phone = clean_phone[2:]
            
        # 7. Automate browser navigation and keystrokes
        if dry_run:
            print(f"  [DRY RUN] Would open WhatsApp Web for {student_name} (+{clean_phone}) with message:")
            print("-" * 40)
            print(message_body)
            print("-" * 40)
            dry_run_messages.append(f"To: {student_name} ({clean_phone})\nMessage:\n{message_body}")
            sent_count += 1
            continue

        try:
            print(f"  💬 Opening WhatsApp Web chat for {student_name} (+{clean_phone})...")
            # Build WhatsApp API URL with text
            encoded_text = quote_plus(message_body)
            whatsapp_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
            
            # Open tab in default browser
            webbrowser.open(whatsapp_url)
            
            # Wait for WhatsApp Web to load
            load_wait_time = 18
            print(f"  ⏳ Waiting {load_wait_time} seconds for page to load. DO NOT touch your mouse/keyboard...")
            time.sleep(load_wait_time)
            
            # Click on the chat input area to guarantee focus
            width, height = pyautogui.size()
            click_x = int(width * 0.60)
            click_y = int(height * 0.90)
            print(f"  🎯 Clicking at screen coordinate ({click_x}, {click_y}) to focus chat box...")
            pyautogui.click(click_x, click_y)
            time.sleep(1.5)  # Wait for click/focus to register
            
            # Press Space to trigger React/JS input state update, then Backspace to keep it clean
            print("  ⌨️ Activating text box state...")
            pyautogui.press('space')
            time.sleep(0.5)
            pyautogui.press('backspace')
            time.sleep(1.0)
            
            # Press 'Enter' key to send the message
            pyautogui.press('enter')
            print("  ✅ Keystroke 'Enter' simulated (Message sent).")
            
            # Wait 7 seconds to ensure message is fully sent before closing tab
            time.sleep(7)
            
            # Press 'Ctrl + W' to close the active tab
            pyautogui.hotkey('ctrl', 'w')
            print("  🚪 Browser tab closed.")
            
            # Update cells to "sent" in Google Sheets
            for skill in pending_skills:
                status_col_1based = skill["status_idx"] + 1
                sheet.update_cell(row_idx, status_col_1based, "sent")
                print(f"  ✅ Updated '{skill['subject'].capitalize()} Status' cell to 'sent'")
            
            # Update Last Sent Date
            sheet.update_cell(row_idx, col_last_sent + 1, current_time_str)
            print(f"  ✅ Updated Last Sent Date for row {row_idx}")
            sent_count += 1
            
            # Give a small 3-second break between different parents
            time.sleep(3)
            
        except Exception as err:
            print(f"  ❌ Failed to send message via WhatsApp Web / update sheet: {err}")
            fail_count += 1

    print("\n-------------------------------------------------------")
    print(f"🏁 Browser Dispatch Completed at {current_time_str}")
    print(f"📬 Sent: {sent_count} | ⚠️ Failed: {fail_count}")
    print("-------------------------------------------------------")

    if dry_run and dry_run_messages:
        output_file = "dry_run_output.txt"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"=== DRY RUN ASSESSMENTS GENERATED AT {current_time_str} ===\n\n")
                for msg in dry_run_messages:
                    f.write(msg + "\n")
                    f.write("=" * 60 + "\n\n")
            print(f"\n📝 Dry-run completed! All {len(dry_run_messages)} generated messages saved to '{output_file}'.")
        except Exception as e:
            print(f"❌ Failed to write dry-run output to file: {e}")

if __name__ == "__main__":
    main()
