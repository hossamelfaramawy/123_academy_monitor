import os
import json
import datetime
from urllib.parse import quote_plus
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client

def main():
    print("🚀 Starting 123 Academy Grid-Based Weekly Exam Dispatcher...")

    # 1. Load Curriculum Data
    try:
        with open("curriculum.json", "r", encoding="utf-8") as f:
            curriculum = json.load(f)
        print(f"📖 Loaded {len(curriculum)} skills from curriculum.json")
    except Exception as e:
        print(f"❌ Error loading curriculum.json: {e}")
        return

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
        creds_dict = json.loads(service_account_json)
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
    try:
        twilio_client = Client(twilio_sid, twilio_token)
        print("✅ Twilio Client initialized successfully")
    except Exception as e:
        print(f"❌ Twilio initialization failed: {e}")
        return

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

    # Map the 12 skill columns to their 0-indexed column coordinates
    subjects = ["math", "arabic", "english"]
    subject_columns = {
        "math": [],     # Stores tuples of (skill_num_1_to_4, col_index)
        "arabic": [],
        "english": []
    }

    # Populate subject columns mapping based on sheet headers
    for idx, header in enumerate(headers):
        for sub in subjects:
            # Check if header matches e.g. "math s1" or "arabic s3"
            if header.startswith(sub + " s"):
                try:
                    skill_num = int(header.split(" s")[1])
                    subject_columns[sub].append((skill_num, idx))
                except ValueError:
                    pass

    # Sort each subject's columns in order of S1, S2, S3, S4
    for sub in subjects:
        subject_columns[sub].sort(key=lambda x: x[0])
        print(f"Mapped {sub.capitalize()} columns: {[f'S{n} (col {c})' for n, c in subject_columns[sub]]}")

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
        if not student_id or not parent_phone or not age_group_str:
            print(f"⚠️ Row {row_idx}: Skipping due to empty student ID, parent phone, or age group.")
            continue

        # Standardize age group (must be 3 or 5)
        try:
            age_group = int(age_group_str)
            if age_group not in [3, 5]:
                raise ValueError
        except ValueError:
            print(f"⚠️ Row {row_idx}: Invalid age group '{age_group_str}' (must be 3 or 5). Skipping.")
            continue

        print(f"\nScanning Row {row_idx}: Student '{student_name}' (ID: {student_id}, Age: {age_group})")

        # Find the first pending skill for each subject
        pending_skills = [] # Stores dicts with skill info

        for sub in subjects:
            cols = subject_columns[sub]
            for skill_num, col_idx in cols:
                # If row is shorter than col_idx, treat value as empty (which implies pending)
                status = ""
                if col_idx < len(row):
                    status = row[col_idx].strip().lower()

                # A skill is eligible to be sent if status is empty, "pending", "sent", or "needs_review"
                # If status is "passed", we skip it and look at the next number (S2, S3, S4)
                if status != "passed":
                    # Generate the curriculum unique ID, e.g., "math_3_s1"
                    skill_id = f"{sub}_{age_group}_s{skill_num}"
                    
                    if skill_id in curriculum:
                        pending_skills.append({
                            "subject": sub,
                            "skill_num": skill_num,
                            "col_idx": col_idx,
                            "skill_id": skill_id,
                            "curriculum_data": curriculum[skill_id]
                        })
                    else:
                        print(f"  ⚠️ Warning: Skill ID '{skill_id}' not found in curriculum.json")
                    
                    # Break out of this subject's S1-S4 loop once we find the first incomplete skill
                    break

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
                col_idx_1based = skill["col_idx"] + 1
                sheet.update_cell(row_idx, col_idx_1based, "sent")
                print(f"  ✅ Updated '{skill['subject'].capitalize()} S{skill['skill_num']}' cell to 'sent'")
            
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

if __name__ == "__main__":
    main()
