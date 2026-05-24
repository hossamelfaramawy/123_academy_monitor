import os
import json
import datetime
from urllib.parse import quote_plus
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client

def main():
    print("🚀 Starting 123 Academy Weekly Exam Dispatcher...")

    # 1. Load Curriculum Data
    try:
        with open("curriculum.json", "r", encoding="utf-8") as f:
            curriculum = json.load(f)
        print(f"📖 Loaded {len(curriculum)} skills from curriculum.json")
    except Exception as e:
        print(f"❌ Error loading curriculum.json: {e}")
        return

    # 2. Get Environment Variables
    github_pages_base = os.environ.get("GITHUB_PAGES_BASE_URL")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Sheet1")
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_sender = os.environ.get("TWILIO_WHATSAPP_SENDER")

    # Validate essential environment variables
    missing_vars = []
    if not github_pages_base: missing_vars.append("GITHUB_PAGES_BASE_URL")
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

    # Map column headers to index (case insensitive lookup)
    try:
        col_student_id = headers.index("student id")
        col_student_name = headers.index("student name")
        col_parent_phone = headers.index("parent phone")
        col_age_group = headers.index("age group")
        col_current_subject = headers.index("current subject")
        col_next_skill = headers.index("next skill id")
        col_last_sent = headers.index("last sent date")
    except ValueError as e:
        print(f"❌ Header structure error: {e}")
        print("Ensure columns match: 'Student ID', 'Student Name', 'Parent Phone', 'Age Group', 'Current Subject', 'Next Skill ID', 'Last Sent Date'")
        return

    # 6. Iterate through student rows and send exams
    sent_count = 0
    fail_count = 0
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # all_records[1:] represents data rows
    for row_idx, row in enumerate(all_records[1:], start=2): # row_idx is 1-indexed for gspread write
        # Check if row is empty or short
        if len(row) <= max(col_student_id, col_student_name, col_parent_phone, col_next_skill):
            continue

        student_id = row[col_student_id].strip()
        student_name = row[col_student_name].strip()
        parent_phone = row[col_parent_phone].strip()
        age_group = row[col_age_group].strip()
        subject = row[col_current_subject].strip().lower()
        next_skill_id = row[col_next_skill].strip()

        # Skip rows with missing critical parameters
        if not student_id or not parent_phone or not next_skill_id:
            print(f"⚠️ Row {row_idx}: Skipping due to empty student ID, parent phone, or next skill ID.")
            continue

        print(f"\nProcessing Row {row_idx}: Student '{student_name}' (ID: {student_id}), Skill: '{next_skill_id}'")

        # Verify skill in curriculum
        if next_skill_id not in curriculum:
            print(f"⚠️ Row {row_idx}: Skill ID '{next_skill_id}' not found in curriculum.json. Skipping.")
            continue

        skill_data = curriculum[next_skill_id]

        # Format URL link
        escaped_name = quote_plus(student_name)
        exam_url = f"{github_pages_base}?student_id={student_id}&skill={next_skill_id}&student_name={escaped_name}"

        # Choose localized messaging template
        is_english_quiz = (subject == "english")
        
        if is_english_quiz:
            skill_title = skill_data.get("title_en", "English Skills")
            message_body = (
                f"Hello Parent of {student_name} 👋\n\n"
                f"It's time for this week's skills challenge for your child at 123 Academy! 🌟\n"
                f"Skill: {skill_title}\n\n"
                f"Please let your little champ click the link below to play the fun interactive game:\n"
                f"{exam_url}\n\n"
                f"Good luck to our hero! 🏆🎈"
            )
        else:
            skill_title = skill_data.get("title_ar", "المهارات التعليمية")
            message_body = (
                f"مرحباً يا ولي أمر {student_name} 👋\n\n"
                f"حان وقت اختبار مهارة هذا الأسبوع لطفلكم المتميز في أكاديمية 123! 🌟\n"
                f"المهارة: {skill_title}\n\n"
                f"يرجى من البطل الصغير الضغط على الرابط التالي لبدء اللعبة التفاعلية الممتعة:\n"
                f"{exam_url}\n\n"
                f"بالتوفيق للبطل! 🏆🎈"
            )

        # Standardize phone number for Twilio (must start with whatsapp:+)
        clean_phone = parent_phone.replace(" ", "").replace("-", "")
        if not clean_phone.startswith("+"):
            # Assume local country prefix or try to fix
            if clean_phone.startswith("00"):
                clean_phone = "+" + clean_phone[2:]
            else:
                clean_phone = "+" + clean_phone
        
        whatsapp_recipient = f"whatsapp:{clean_phone}"

        # Send WhatsApp message
        try:
            print(f"Sending WhatsApp message to {whatsapp_recipient} via Twilio...")
            message = twilio_client.messages.create(
                body=message_body,
                from_=twilio_sender,
                to=whatsapp_recipient
            )
            print(f"✅ Success! Message SID: {message.sid}")
            
            # Update the sheet with last sent date
            # Column coordinates in gspread are 1-indexed, so add 1 to the 0-indexed column index
            sheet.update_cell(row_idx, col_last_sent + 1, current_time_str)
            print(f"✅ Updated Last Sent Date in Google Sheet for row {row_idx}")
            sent_count += 1
            
        except Exception as err:
            print(f"❌ Failed to send message/update sheet: {err}")
            fail_count += 1

    print("\n-------------------------------------------------------")
    print(f"🏁 Dispatch Completed at {current_time_str}")
    print(f"📬 Sent: {sent_count} | ⚠️ Failed: {fail_count}")
    print("-------------------------------------------------------")

if __name__ == "__main__":
    main()
