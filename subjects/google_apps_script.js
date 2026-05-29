/**
 * 123 Academy - Student Progress Tracker Backend (Google Apps Script)
 * 
 * Instructions:
 * 1. Open your Google Spreadsheet.
 * 2. Click "Extensions" -> "Apps Script".
 * 3. Clear any existing code in the editor and paste this code.
 * 4. Click the "Save" (disk) icon.
 * 5. Click "Deploy" (top right) -> "New deployment".
 * 6. Select type "Web app".
 * 7. Set configuration:
 *    - Description: "123 Academy Progress API"
 *    - Execute as: "Me" (your email)
 *    - Who has access: "Anyone" (essential for frontend access without OAuth)
 * 8. Click "Deploy".
 * 9. Copy the "Web app URL" and use it in your index.html and dashboard.html.
 */

// Configure sheet names
const MAIN_SHEET_NAME = "Sheet1";
const LOG_SHEET_NAME = "Quiz Logs";

function doGet(e) {
  try {
    const params = e.parameter;
    const studentId = params.student_id;
    
    if (!studentId) {
      return jsonResponse({ success: false, error: "Missing student_id parameter" });
    }
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const mainSheet = spreadsheet.getSheetByName(MAIN_SHEET_NAME);
    
    if (!mainSheet) {
      return jsonResponse({ success: false, error: "Main sheet 'Sheet1' not found" });
    }
    
    // 1. Find student row in Sheet1
    const mainData = mainSheet.getDataRange().getValues();
    const mainHeaders = mainData[0].map(h => h.toString().trim().toLowerCase());
    
    const studentIdColIdx = mainHeaders.indexOf("student id");
    const studentNameColIdx = mainHeaders.indexOf("student name");
    const ageGroupColIdx = mainHeaders.indexOf("age group");
    
    if (studentIdColIdx === -1) {
      return jsonResponse({ success: false, error: "'Student ID' column not found in Sheet1" });
    }
    
    let studentRow = null;
    for (let i = 1; i < mainData.length; i++) {
      if (mainData[i][studentIdColIdx].toString().trim() === studentId.toString().trim()) {
        studentRow = mainData[i];
        break;
      }
    }
    
    if (!studentRow) {
      return jsonResponse({ success: false, error: "Student not found with ID " + studentId });
    }
    
    const studentName = studentNameColIdx !== -1 ? studentRow[studentNameColIdx] : "Student";
    const ageGroup = ageGroupColIdx !== -1 ? studentRow[ageGroupColIdx] : 3;
    
    // Parse current subject levels/statuses
    const currentStatus = {};
    const subjects = ["math", "arabic", "english"];
    subjects.forEach(subject => {
      const lvlColIdx = mainHeaders.indexOf(subject + " level");
      const statColIdx = mainHeaders.indexOf(subject + " status");
      
      currentStatus[subject] = {
        level: lvlColIdx !== -1 ? studentRow[lvlColIdx].toString().trim() : "",
        status: statColIdx !== -1 ? studentRow[statColIdx].toString().trim() : ""
      };
    });
    
    // 2. Fetch history from Quiz Logs
    const history = [];
    let logSheet = spreadsheet.getSheetByName(LOG_SHEET_NAME);
    if (logSheet) {
      const logData = logSheet.getDataRange().getValues();
      if (logData.length > 1) {
        const logHeaders = logData[0].map(h => h.toString().trim().toLowerCase());
        const logStudentIdColIdx = logHeaders.indexOf("student id");
        const timestampColIdx = logHeaders.indexOf("timestamp");
        const subjectColIdx = logHeaders.indexOf("subject");
        const skillIdColIdx = logHeaders.indexOf("skill id");
        const levelTitleColIdx = logHeaders.indexOf("level title");
        const scoreColIdx = logHeaders.indexOf("score");
        const totalColIdx = logHeaders.indexOf("total");
        const statusColIdx = logHeaders.indexOf("status");
        
        for (let i = 1; i < logData.length; i++) {
          if (logStudentIdColIdx !== -1 && logData[i][logStudentIdColIdx].toString().trim() === studentId.toString().trim()) {
            history.push({
              timestamp: timestampColIdx !== -1 ? logData[i][timestampColIdx] : "",
              subject: subjectColIdx !== -1 ? logData[i][subjectColIdx] : "",
              skill_id: skillIdColIdx !== -1 ? logData[i][skillIdColIdx] : "",
              level_title: levelTitleColIdx !== -1 ? logData[i][levelTitleColIdx] : "",
              score: scoreColIdx !== -1 ? Number(logData[i][scoreColIdx]) : 0,
              total: totalColIdx !== -1 ? Number(logData[i][totalColIdx]) : 5,
              status: statusColIdx !== -1 ? logData[i][statusColIdx] : ""
            });
          }
        }
      }
    }
    
    // Sort history by date descending (newest first)
    history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    return jsonResponse({
      success: true,
      student_id: studentId,
      student_name: studentName,
      age_group: ageGroup,
      current_status: currentStatus,
      history: history
    });
    
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

function doPost(e) {
  try {
    let postData;
    if (e.postData && e.postData.contents) {
      postData = JSON.parse(e.postData.contents);
    } else {
      postData = e.parameter;
    }
    
    const studentId = postData.student_id;
    const studentName = postData.student_name;
    const skillId = postData.skill_id;
    const subject = postData.subject || skillId.split('_')[0] || "english";
    const levelTitle = postData.level_title || "Quiz";
    const score = Number(postData.score);
    const total = Number(postData.total || 5);
    const status = postData.status; // "Passed" or "Needs Review"
    
    if (!studentId || !skillId) {
      return jsonResponse({ success: false, error: "Missing required student_id or skill_id" });
    }
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    
    // 1. Get or create 'Quiz Logs' sheet
    let logSheet = spreadsheet.getSheetByName(LOG_SHEET_NAME);
    if (!logSheet) {
      logSheet = spreadsheet.insertSheet(LOG_SHEET_NAME);
      // Create headers
      logSheet.appendRow([
        "Timestamp",
        "Student ID",
        "Student Name",
        "Subject",
        "Skill ID",
        "Level Title",
        "Score",
        "Total",
        "Status"
      ]);
      // Format headers bold
      logSheet.getRange("A1:I1").setFontWeight("bold");
    }
    
    // Append the quiz attempt row
    const timestampStr = new Date().toISOString();
    logSheet.appendRow([
      timestampStr,
      studentId,
      studentName,
      subject,
      skillId,
      levelTitle,
      score,
      total,
      status
    ]);
    
    // 2. Update Student Status in Sheet1
    const mainSheet = spreadsheet.getSheetByName(MAIN_SHEET_NAME);
    if (mainSheet) {
      const mainData = mainSheet.getDataRange().getValues();
      const mainHeaders = mainData[0].map(h => h.toString().trim().toLowerCase());
      
      const studentIdColIdx = mainHeaders.indexOf("student id");
      const statusColIdx = mainHeaders.indexOf(subject.toLowerCase() + " status");
      
      if (studentIdColIdx !== -1 && statusColIdx !== -1) {
        let matchedRowIdx = -1;
        for (let i = 1; i < mainData.length; i++) {
          if (mainData[i][studentIdColIdx].toString().trim() === studentId.toString().trim()) {
            matchedRowIdx = i + 1; // 1-indexed row number
            break;
          }
        }
        
        if (matchedRowIdx !== -1) {
          // Update Sheet1 status cell
          // Convert Status: Passed -> passed, Needs Review -> needs_review
          const formattedStatus = (status.toLowerCase() === "passed") ? "passed" : "needs_review";
          mainSheet.getRange(matchedRowIdx, statusColIdx + 1).setValue(formattedStatus);
        }
      }
    }
    
    return jsonResponse({ success: true, message: "Quiz result logged successfully" });
    
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

// Helper to return CORS-friendly JSON response
function jsonResponse(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
