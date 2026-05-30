import os
import json
import datetime
import sys
from urllib.parse import quote_plus
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client

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
    # Check if running in dry-run mode
    dry_run = "--dry-run" in sys.argv or os.environ.get("DRY_RUN", "").lower() == "true"
    dry_run_messages = []

    if dry_run:
        print("🧪 RUNNING IN DRY-RUN (TEST) MODE - Messages will not be sent, Google Sheet will not be modified.")
    else:
        print("🚀 Starting 123 Academy Grid-Based Weekly Exam Dispatcher...")

    # 1. Load Curriculum Data from subject subdirectories
    curriculum = {}
    
    # Load Arabic & Math (global files)
    global_subjects = {
        "math": "subjects/math/math_curriculum.json",
        "arabic": "subjects/arabic/ar_curriculum.json"
    }
    for sub, path in global_subjects.items():
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
            
    # Load English (split letter files)
    english_curriculum_dir = "subjects/english/curriculum"
    if os.path.exists(english_curriculum_dir):
        try:
            count = 0
            for filename in os.listdir(english_curriculum_dir):
                if filename.endswith(".json"):
                    path = os.path.join(english_curriculum_dir, filename)
                    with open(path, "r", encoding="utf-8") as f:
                        sub_data = json.load(f)
                        curriculum.update(sub_data)
                        count += len(sub_data)
            print(f"  📖 Loaded {count} skills from English split curriculum files")
        except Exception as e:
            print(f"  ⚠️ Error loading split English curriculum: {e}")
            return
    else:
        print(f"  ℹ️ English split curriculum folder '{english_curriculum_dir}' not found (skipping)")
            
    print(f"📖 Combined total: Loaded {len(curriculum)} skills across all subjects.")

    # 2. Get Environment Variables
    github_pages_base = os.environ.get("PAGES_BASE_URL")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Sheet1")
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_sender = os.environ.get("TWILIO_WHATSAPP_SENDER")

    # Safe debug prints to verify variables are loaded
    print("📋 Loaded Environment Variables Configuration:")
    print(f"  - PAGES_BASE_URL: '{github_pages_base}'")
    print(f"  - GOOGLE_SHEET_ID: '{sheet_id[:6]}...'" if sheet_id else "  - GOOGLE_SHEET_ID: None")
    print(f"  - GOOGLE_SHEET_NAME: '{sheet_name}'")
    print(f"  - GOOGLE_SERVICE_ACCOUNT_JSON: {'[PRESENT]' if service_account_json else '[MISSING]'}")
    print(f"  - TWILIO_ACCOUNT_SID: '{twilio_sid[:8]}...'" if twilio_sid else "  - TWILIO_ACCOUNT_SID: None")
    print(f"  - TWILIO_AUTH_TOKEN: {'[PRESENT]' if twilio_token else '[MISSING]'}")
    print(f"  - TWILIO_WHATSAPP_SENDER: '{twilio_sender}'")

    # Validate essential environment variables
    missing_vars = []
    if not github_pages_base: missing_vars.append("PAGES_BASE_URL")
    if not sheet_id: missing_vars.append("GOOGLE_SHEET_ID")
    if not service_account_json: missing_vars.append("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not dry_run:
        if not twilio_sid: missing_vars.append("TWILIO_ACCOUNT_SID")
        if not twilio_token: missing_vars.append("TWILIO_AUTH_TOKEN")
        if not twilio_sender: missing_vars.append("TWILIO_WHATSAPP_SENDER")

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Stopping execution.")
        return

    # Make sure GitHub Pages URL ends with a slash
    if not github_pages_base.endswith("/"):
        github_pages_base += "/"

    # 3. Authenticate with Google Sheets API
    try:
        # Check if the variable points to a local .json file
        clean_json_val = service_account_json.strip()
        if clean_json_val.endswith(".json") and os.path.exists(clean_json_val):
            print(f"📂 Loading Google credentials from local key file: '{clean_json_val}'")
            with open(clean_json_val, "r", encoding="utf-8") as f:
                creds_dict = json.load(f)
        else:
            try:
                creds_dict = json.loads(service_account_json)
            except json.JSONDecodeError as je:
                # Try to recover by replacing single quotes with double quotes
                try:
                    fixed_json = service_account_json.replace("'", '"')
                    creds_dict = json.loads(fixed_json)
                    print("⚠️ Note: Automatically corrected single quotes to double quotes in Google JSON credentials.")
                except Exception:
                    print(f"❌ Google Credentials JSON Parse Error: {je}")
                    print(f"  Value starts with: '{service_account_json[:50]}...'")
                    print(f"  Is file path check: exists={os.path.exists(clean_json_val)}")
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

    # 4. Initialize Twilio client
    twilio_client = None
    if not dry_run:
        try:
            twilio_client = Client(twilio_sid, twilio_token)
            print("✅ Twilio Client initialized successfully")
        except Exception as e:
            print(f"❌ Twilio initialization failed: {e}")
            return
    else:
        print("⏭️ Dry-run: Skipping Twilio Client initialization")

    # 5. Read Spreadsheet and Header Mapping
    all_records = sheet.get_all_values()
    if len(all_records) < 2:
        print("⚠️ Spreadsheet is empty or only has headers. No students to notify.")
        return

    headers = [h.strip().lower() for h in all_records[0]]
    print(f"Headers found: {headers}")

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

    # 6. Iterate through student rows and send exams
    sent_count = 0
    fail_count = 0
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # all_records[1:] represents data rows
    for row_idx, row in enumerate(all_records[1:], start=2): # row_idx is 1-indexed for gspread write
        # Check if row is empty or short
        if len(row) <= max(col_student_id, col_student_name, col_parent_phone, col_age_group):
            continue

        student_id = row[col_student_id].strip()
        student_name = row[col_student_name].strip()
        parent_phone = row[col_parent_phone].strip()
        age_group_str = row[col_age_group].strip()

        # Skip rows with missing critical parameters
        if not student_id or not parent_phone:
            print(f"⚠️ Row {row_idx}: Skipping due to empty student ID or parent phone.")
            continue

        try:
            age_group = int(age_group_str)
        except ValueError:
            age_group = 3  # default to age group 3 if missing or invalid

        print(f"\nScanning Row {row_idx}: Student '{student_name}' (ID: {student_id}, Age: {age_group})")

        # Find the pending skill for each subject using level & status pairs
        pending_skills = [] # Stores dicts with skill info

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
            print(f"  ℹ️ No pending skills to send for '{student_name}' (all skills are completed/passed).")
            continue

        # 7. Construct combined WhatsApp message
        message_lines = []
        message_lines.append(f"مرحباً يا ولي أمر {student_name} 👋")
        message_lines.append("")
        message_lines.append("حان وقت الألعاب التعليمية التفاعلية لهذا الأسبوع لطفلكم المتميز في أكاديمية 123! 🌟")
        message_lines.append("الرجاء من البطل الصغير حل التحديات التالية:")
        message_lines.append("")

        # Subject Display Translation Maps
        subject_metadata = {
            "math": {"emoji": "➕", "name": "الرياضيات (Math)", "title_key": "title_ar"},
            "arabic": {"emoji": "✏️", "name": "اللغة العربية (Arabic)", "title_key": "title_ar"},
            "english": {"emoji": "🔤", "name": "اللغة الإنجليزية (English)", "title_key": "title_en"}
        }

        for skill in pending_skills:
            sub = skill["subject"]
            meta = subject_metadata[sub]
            skill_id = skill["skill_id"]
            
            # Fetch localized title
            title_key = meta["title_key"]
            skill_title = skill["curriculum_data"].get(title_key, skill_id)
            
            # Build URL Link
            escaped_name = quote_plus(student_name)
            exam_url = f"{github_pages_base}?student_id={student_id}&skill={skill_id}&student_name={escaped_name}"
            
            message_lines.append(f"{meta['emoji']} *{meta['name']}: {skill_title}*")
            message_lines.append(f"🔗 رابط اللعبة: {exam_url}")
            message_lines.append("")

        message_lines.append("بالتوفيق للبطل! 🏆🎈")
        message_body = "\n".join(message_lines)

        # Standardize phone number for Twilio (must start with whatsapp:+)
        clean_phone = parent_phone.replace(" ", "").replace("-", "")
        if not clean_phone.startswith("+"):
            if clean_phone.startswith("00"):
                clean_phone = "+" + clean_phone[2:]
            else:
                clean_phone = "+" + clean_phone
        
        whatsapp_recipient = f"whatsapp:{clean_phone}"

        # 8. Dispatch WhatsApp Message
        if dry_run:
            print(f"  [DRY RUN] Would send combined WhatsApp to {whatsapp_recipient}:")
            print("-" * 40)
            print(message_body)
            print("-" * 40)
            dry_run_messages.append(f"To: {student_name} ({whatsapp_recipient})\nMessage:\n{message_body}")
            sent_count += 1
            continue

        try:
            print(f"  Sending combined WhatsApp to {whatsapp_recipient} via Twilio...")
            message = twilio_client.messages.create(
                body=message_body,
                from_=twilio_sender,
                to=whatsapp_recipient
            )
            print(f"  ✅ Twilio Success! SID: {message.sid}")
            
            # Update cells to "sent" in Google Sheets
            for skill in pending_skills:
                status_col_1based = skill["status_idx"] + 1
                sheet.update_cell(row_idx, status_col_1based, "sent")
                print(f"  ✅ Updated '{skill['subject'].capitalize()} Status' cell to 'sent'")
            
            # Update Last Sent Date
            sheet.update_cell(row_idx, col_last_sent + 1, current_time_str)
            print(f"  ✅ Updated Last Sent Date for row {row_idx}")
            sent_count += 1
            
        except Exception as err:
            print(f"  ❌ Failed to send message / update sheet cells for '{student_name}': {err}")
            fail_count += 1

    print("\n-------------------------------------------------------")
    print(f"🏁 Dispatch Completed at {current_time_str}")
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
