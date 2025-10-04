// Exam Results Marking Module
document.addEventListener("DOMContentLoaded", function () {
  let currentExamId = null;
  let currentSubject = null;
  let csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");

  // Initialize
  loadAssignedExams();

  // Event listeners
  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("exam-item")) {
      selectExam(e.target);
    } else if (e.target.classList.contains("subject-item")) {
      selectSubject(e.target);
    }
  });

  document
    .getElementById("save-draft-btn")
    .addEventListener("click", saveDraft);
  document
    .getElementById("submit-results-btn")
    .addEventListener("click", submitResults);

  function showMessage(message, type = "success") {
    const messagesDiv = document.getElementById("messages");
    messagesDiv.innerHTML = `<div class="message ${type}">${message}</div>`;
    setTimeout(() => {
      messagesDiv.innerHTML = "";
    }, 5000);
  }

  function setLoading(element, text = "Loading...") {
    element.innerHTML = `<div class="loading">${text}</div>`;
  }

  function loadAssignedExams() {
    const examList = document.getElementById("exam-list");
    setLoading(examList, "Loading assigned exams...");

    fetch(window.location.href, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken ? csrfToken.value : "",
      },
      body: "action=get_assigned_exams",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          if (data.exams.length === 0) {
            examList.innerHTML = "<p>No exams assigned to you.</p>";
            return;
          }

          examList.innerHTML = data.exams
            .map(
              (exam) => `
                <div class="exam-item" data-exam-id="${exam.id}">
                  <h3>${exam.name}</h3>
                  <p><strong>Term:</strong> ${exam.term}</p>
                  <p><strong>Date:</strong> ${exam.date}</p>
                </div>
              `
            )
            .join("");
        } else {
          examList.innerHTML = `<p class="error">Error: ${data.error}</p>`;
        }
      })
      .catch((error) => {
        examList.innerHTML = `<p class="error">Error loading exams: ${error.message}</p>`;
      });
  }

  function selectExam(examElement) {
    // Remove previous selection
    document.querySelectorAll(".exam-item").forEach((item) => {
      item.classList.remove("selected");
    });

    // Select current
    examElement.classList.add("selected");
    currentExamId = examElement.dataset.examId;

    // Show subject selection
    document.getElementById("exam-selection").classList.remove("active");
    document.getElementById("subject-selection").classList.add("active");

    // Load subjects
    loadSubjects();
  }

  function loadSubjects() {
    const subjectList = document.getElementById("subject-list");
    setLoading(subjectList, "Loading subjects...");

    fetch(window.location.href, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken ? csrfToken.value : "",
      },
      body: `action=get_subjects&exam_id=${currentExamId}`,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          if (data.subjects.length === 0) {
            subjectList.innerHTML = "<p>No subjects found for this exam.</p>";
            return;
          }

          subjectList.innerHTML = data.subjects
            .map(
              (subject) => `
                <div class="subject-item" data-subject="${subject}">
                  <h3>${subject}</h3>
                </div>
              `
            )
            .join("");
        } else {
          subjectList.innerHTML = `<p class="error">Error: ${data.error}</p>`;
        }
      })
      .catch((error) => {
        subjectList.innerHTML = `<p class="error">Error loading subjects: ${error.message}</p>`;
      });
  }

  function selectSubject(subjectElement) {
    // Remove previous selection
    document.querySelectorAll(".subject-item").forEach((item) => {
      item.classList.remove("selected");
    });

    // Select current
    subjectElement.classList.add("selected");
    currentSubject = subjectElement.dataset.subject;

    // Show results marking
    document.getElementById("subject-selection").classList.remove("active");
    document.getElementById("results-marking").classList.add("active");

    // Load students
    loadStudents();
  }

  function loadStudents() {
    const container = document.getElementById("students-table-container");
    setLoading(container, "Loading students...");

    fetch(window.location.href, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken ? csrfToken.value : "",
      },
      body: `action=get_students&exam_id=${currentExamId}&subject=${encodeURIComponent(
        currentSubject
      )}`,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          if (data.students.length === 0) {
            container.innerHTML = "<p>No students found.</p>";
            return;
          }

          container.innerHTML = `
            <table class="students-table">
              <thead>
                <tr>
                  <th>Student Name</th>
                  <th>Roll No</th>
                  <th>Class</th>
                  <th>Max Marks</th>
                  <th>Marks Obtained</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                ${data.students
                  .map(
                    (student) => `
                      <tr class="${
                        student.is_locked ? "locked-row" : ""
                      }" data-student-id="${student.id}">
                        <td>${student.name}</td>
                        <td>${student.roll_no}</td>
                        <td>${student.class}</td>
                        <td>${data.total_marks}</td>
                        <td>
                          <input type="number"
                                 class="marks-input"
                                 min="0"
                                 max="${data.total_marks}"
                                 value="${student.marks_obtained}"
                                 ${student.is_locked ? "disabled" : ""}
                                 data-student-id="${student.id}">
                        </td>
                        <td>
                          <input type="text"
                                 class="remarks-input"
                                 value="${student.remarks || ""}"
                                 ${student.is_locked ? "disabled" : ""}
                                 data-student-id="${student.id}">
                        </td>
                      </tr>
                    `
                  )
                  .join("")}
              </tbody>
            </table>
          `;
        } else {
          container.innerHTML = `<p class="error">Error: ${data.error}</p>`;
        }
      })
      .catch((error) => {
        container.innerHTML = `<p class="error">Error loading students: ${error.message}</p>`;
      });
  }

  function collectStudentMarks() {
    const marksData = {};
    const rows = document.querySelectorAll(
      ".students-table tbody tr:not(.locked-row)"
    );

    rows.forEach((row) => {
      const studentId = row.dataset.studentId;
      const marksInput = row.querySelector(".marks-input");
      const remarksInput = row.querySelector(".remarks-input");

      if (marksInput && remarksInput) {
        marksData[studentId] = {
          marks: marksInput.value.trim(),
          remarks: remarksInput.value.trim(),
        };
      }
    });

    return marksData;
  }

  function saveDraft() {
    if (!currentExamId || !currentSubject) {
      showMessage("Please select an exam and subject first.", "error");
      return;
    }

    const studentMarks = collectStudentMarks();

    if (Object.keys(studentMarks).length === 0) {
      showMessage("No students to save.", "error");
      return;
    }

    // Disable button
    const btn = document.getElementById("save-draft-btn");
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Saving...';
    btn.disabled = true;

    fetch(window.location.href, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken ? csrfToken.value : "",
      },
      body: `action=save_draft&exam_id=${currentExamId}&subject=${encodeURIComponent(
        currentSubject
      )}&student_marks=${encodeURIComponent(JSON.stringify(studentMarks))}`,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showMessage(data.message, "success");
        } else {
          showMessage(data.error, "error");
        }
      })
      .catch((error) => {
        showMessage(`Error saving draft: ${error.message}`, "error");
      })
      .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      });
  }

  function submitResults() {
    if (!currentExamId || !currentSubject) {
      showMessage("Please select an exam and subject first.", "error");
      return;
    }

    const studentMarks = collectStudentMarks();

    if (Object.keys(studentMarks).length === 0) {
      showMessage("No students to submit.", "error");
      return;
    }

    // Check if all marks are entered
    const missingMarks = [];
    Object.entries(studentMarks).forEach(([studentId, data]) => {
      if (!data.marks) {
        const row = document.querySelector(
          `tr[data-student-id="${studentId}"]`
        );
        if (row) {
          const name = row.cells[0].textContent;
          missingMarks.push(name);
        }
      }
    });

    if (missingMarks.length > 0) {
      showMessage(
        `Please enter marks for: ${missingMarks.join(", ")}`,
        "error"
      );
      return;
    }

    if (
      !confirm(
        "Are you sure you want to submit and lock these results? You cannot edit them afterwards."
      )
    ) {
      return;
    }

    // Disable button
    const btn = document.getElementById("submit-results-btn");
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Submitting...';
    btn.disabled = true;

    fetch(window.location.href, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken ? csrfToken.value : "",
      },
      body: `action=submit_results&exam_id=${currentExamId}&subject=${encodeURIComponent(
        currentSubject
      )}&student_marks=${encodeURIComponent(JSON.stringify(studentMarks))}`,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showMessage(data.message, "success");
          // Reload students to show locked state
          loadStudents();
        } else {
          showMessage(data.error, "error");
          if (data.details) {
            showMessage(data.details.join("<br>"), "error");
          }
        }
      })
      .catch((error) => {
        showMessage(`Error submitting results: ${error.message}`, "error");
      })
      .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      });
  }
});
