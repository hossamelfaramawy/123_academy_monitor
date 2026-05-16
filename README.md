# 123 Academy - Exam Monitor System (MVP)

This repository is used as a static hosting server for the interactive HTML exams of **123 Academy**. 

## 🚀 Purpose
It provides stable, live web links for the kindergarten children's skills assessment. These links are dynamically generated and sent to parents via WhatsApp by our AI Agent.

## 🛠️ How it works
1. The AI Agent checks the student's current pending skill from the Google Sheets tracker (`MVP_Skills_Tracker.xlsx`).
2. It sends this repository's live link appended with parameters (e.g., `?student_id=1&skill=skill_1`) to the parent.
3. Once the child finishes the interactive quiz, the embedded JavaScript submits the results directly via Webhook to **Make.com** to update the database automatically.
