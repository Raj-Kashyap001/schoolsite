document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("searchInput");
  const statusFilter = document.getElementById("statusFilter");
  const pendingTable = document
    .getElementById("pendingTable")
    .querySelector("tbody");
  const markedTable = document
    .getElementById("markedTable")
    .querySelector("tbody");
  const commitBtn = document.querySelector(".btn-primary");

  // Disable export buttons if no attendance is marked
  function updateExportButtons() {
    const markedRows = markedTable.querySelectorAll("tbody tr");
    const hasMarkedAttendance = markedRows.length > 0;
    const exportCsvBtn = document.getElementById("exportCsv");
    const exportExcelBtn = document.getElementById("exportExcel");
    const exportJsonBtn = document.getElementById("exportJson");

    if (!hasMarkedAttendance) {
      exportCsvBtn.disabled = true;
      exportExcelBtn.disabled = true;
      exportJsonBtn.disabled = true;
      exportCsvBtn.title = "No attendance marked yet";
      exportExcelBtn.title = "No attendance marked yet";
      exportJsonBtn.title = "No attendance marked yet";
      exportCsvBtn.classList.add("disabled");
      exportExcelBtn.classList.add("disabled");
      exportJsonBtn.classList.add("disabled");
    } else {
      exportCsvBtn.disabled = false;
      exportExcelBtn.disabled = false;
      exportJsonBtn.disabled = false;
      exportCsvBtn.title = "";
      exportExcelBtn.title = "";
      exportJsonBtn.title = "";
      exportCsvBtn.classList.remove("disabled");
      exportExcelBtn.classList.remove("disabled");
      exportJsonBtn.classList.remove("disabled");
    }
  }

  // Initial check
  updateExportButtons();

  function filterRows() {
    const searchTerm = searchInput.value.toLowerCase();
    const statusValue = statusFilter.value;
    const rows = pendingTable.querySelectorAll(".student-row");

    rows.forEach((row) => {
      const name = row.dataset.name;
      const roll = row.dataset.roll;
      const className = row.dataset.class;
      const matchesSearch =
        name.includes(searchTerm) ||
        roll.includes(searchTerm) ||
        className.includes(searchTerm);

      let matchesStatus = true;
      if (statusValue) {
        const checkedRadio = row.querySelector('input[type="radio"]:checked');
        matchesStatus = checkedRadio && checkedRadio.value === statusValue;
      }

      row.style.display = matchesSearch && matchesStatus ? "" : "none";
    });
  }

  searchInput.addEventListener("input", filterRows);
  statusFilter.addEventListener("change", filterRows);

  // Undo functionality
  document.querySelectorAll(".undo-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const studentId = this.getAttribute("data-student-id");
      const formData = new FormData();
      formData.append(
        "csrfmiddlewaretoken",
        document.querySelector("[name=csrfmiddlewaretoken]").value
      );
      formData.append("action", "undo");
      formData.append("student_id", studentId);

      fetch(window.location.href, {
        method: "POST",
        body: formData,
      })
        .then((response) => {
          if (response.ok) {
            location.reload();
          }
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    });
  });

  // Toolbar buttons
  document.getElementById("importCsv").addEventListener("click", () => {
    // Check if user is teacher or admin - both can import
    const userRole =
      document.querySelector("body").dataset.userRole || "Teacher";
    if (userRole === "Teacher" || userRole === "Admin") {
      showImportModal();
    } else {
      alert(
        "Access denied. Only teachers and admins can import attendance data."
      );
    }
  });

  document.getElementById("importExcel").addEventListener("click", () => {
    // Check if user is teacher or admin - both can import
    const userRole =
      document.querySelector("body").dataset.userRole || "Teacher";
    if (userRole === "Teacher" || userRole === "Admin") {
      showExcelImportModal();
    } else {
      alert(
        "Access denied. Only teachers and admins can import attendance data."
      );
    }
  });

  document.getElementById("exportCsv").addEventListener("click", () => {
    // Check if user is teacher or admin - if yes, export current date data directly
    // Otherwise show modal for other roles
    const userRole =
      document.querySelector("body").dataset.userRole || "Teacher";
    if (userRole === "Teacher" || userRole === "Admin") {
      handleTeacherCsvExport();
    } else {
      handleCsvExport();
    }
  });

  document.getElementById("exportExcel").addEventListener("click", () => {
    // Check if user is teacher or admin - if yes, export current date data directly
    // Otherwise show modal for other roles
    const userRole =
      document.querySelector("body").dataset.userRole || "Teacher";
    if (userRole === "Teacher" || userRole === "Admin") {
      handleTeacherExcelExport();
    } else {
      handleExcelExport();
    }
  });

  document.getElementById("exportJson").addEventListener("click", () => {
    // Check if user is teacher - if yes, export current date data directly
    // Otherwise show modal for admin
    const userRole =
      document.querySelector("body").dataset.userRole || "Teacher";
    if (userRole === "Teacher") {
      handleTeacherJsonExport();
    } else {
      handleJsonExport();
    }
  });

  // Show Import Modal
  function showImportModal() {
    const modal = document.createElement("div");
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); display: flex; align-items: center;
      justify-content: center; z-index: 1000;
    `;

    const modalContent = document.createElement("div");
    modalContent.style.cssText = `
      background: white; padding: 20px; border-radius: 8px;
      max-width: 500px; max-height: 80vh; overflow-y: auto;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;

    modalContent.innerHTML = `
      <h3>Import Attendance from CSV</h3>

      <div style="margin: 20px 0;">
        <h4>CSV Format Requirements:</h4>
        <ul style="margin: 10px 0; padding-left: 20px;">
          <li>Required columns: <code>student_name</code>, <code>roll_no</code>, <code>class</code>, <code>status</code>, <code>date</code></li>
          <li>Optional column: <code>remarks</code></li>
          <li>Status values: <code>PRESENT</code>, <code>ABSENT</code>, <code>LATE</code></li>
          <li>Date format: <code>DD-MM-YY</code>, <code>DD-MM-YYYY</code>, <code>DD/MM/YY</code>, <code>DD/MM/YYYY</code>, or <code>YYYY-MM-DD</code> (e.g., 15-01-24, 15-01-2024, 15/01/24, 15/01/2024, or 2024-01-15)</li>
          <li>First row should be headers</li>
        </ul>
        <div style="margin-top: 15px;">
          <a href="/dashboard/attendance/template/" class="btn btn-outline" style="font-size: 14px; padding: 8px 12px;">
            <i class="bx bx-download"></i> Download CSV Template
          </a>
        </div>
      </div>

      <div style="margin: 20px 0;">
        <label for="csvFile" style="display: block; margin-bottom: 10px; font-weight: bold;">Select CSV File:</label>
        <input type="file" id="csvFile" accept=".csv" style="width: 100%; padding: 8px; margin: 5px 0;">
      </div>

      <div id="importErrors" style="margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; display: none;">
        <h4 style="color: #dc3545; margin: 0 0 10px 0;">Import Errors:</h4>
        <div id="errorsList" style="max-height: 150px; overflow-y: auto;"></div>
      </div>

      <div id="importSuccess" style="margin: 15px 0; padding: 10px; background: #d4edda; border-radius: 4px; display: none;">
        <h4 style="color: #155724; margin: 0 0 10px 0;">Import Successful!</h4>
        <p id="successMessage" style="margin: 0;"></p>
      </div>

      <div style="text-align: right; margin-top: 20px;">
        <button class="btn btn-outline btn-cancel" style="margin-right: 10px;">Cancel</button>
        <button class="btn btn-primary btn-import" disabled>Import CSV</button>
      </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // Event handlers
    const cancelBtn = modal.querySelector(".btn-cancel");
    const importBtn = modal.querySelector(".btn-import");
    const fileInput = modal.querySelector("#csvFile");

    cancelBtn.addEventListener("click", () => {
      document.body.removeChild(modal);
    });

    fileInput.addEventListener("change", (e) => {
      importBtn.disabled = !e.target.files[0];
    });

    importBtn.addEventListener("click", () => {
      const file = fileInput.files[0];
      if (file) {
        handleCsvImport(file, modal, importBtn);
      }
    });
  }

  // Show Excel Import Modal
  function showExcelImportModal() {
    const modal = document.createElement("div");
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); display: flex; align-items: center;
      justify-content: center; z-index: 1000;
    `;

    const modalContent = document.createElement("div");
    modalContent.style.cssText = `
      background: white; padding: 20px; border-radius: 8px;
      max-width: 500px; max-height: 80vh; overflow-y: auto;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;

    modalContent.innerHTML = `
      <h3>Import Attendance from Excel</h3>

      <div style="margin: 20px 0;">
        <h4>Excel Format Requirements:</h4>
        <ul style="margin: 10px 0; padding-left: 20px;">
          <li>Required columns: <code>student_name</code>, <code>roll_no</code>, <code>class</code>, <code>status</code>, <code>date</code></li>
          <li>Optional column: <code>remarks</code></li>
          <li>Status values: <code>PRESENT</code>, <code>ABSENT</code>, <code>LATE</code></li>
          <li>Date format: <code>DD-MM-YY</code>, <code>DD-MM-YYYY</code>, <code>DD/MM/YY</code>, <code>DD/MM/YYYY</code>, or <code>YYYY-MM-DD</code> (e.g., 15-01-24, 15-01-2024, 15/01/24, 15/01/2024, or 2024-01-15)</li>
          <li>First row should be headers</li>
        </ul>
        <div style="margin-top: 15px;">
          <a href="/dashboard/attendance/excel-template/" class="btn btn-outline" style="font-size: 14px; padding: 8px 12px;">
            <i class="bx bx-download"></i> Download Excel Template
          </a>
        </div>
      </div>

      <div style="margin: 20px 0;">
        <label for="excelFile" style="display: block; margin-bottom: 10px; font-weight: bold;">Select Excel File:</label>
        <input type="file" id="excelFile" accept=".xlsx,.xls" style="width: 100%; padding: 8px; margin: 5px 0;">
      </div>

      <div id="excelImportErrors" style="margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; display: none;">
        <h4 style="color: #dc3545; margin: 0 0 10px 0;">Import Errors:</h4>
        <div id="excelErrorsList" style="max-height: 150px; overflow-y: auto;"></div>
      </div>

      <div id="excelImportSuccess" style="margin: 15px 0; padding: 10px; background: #d4edda; border-radius: 4px; display: none;">
        <h4 style="color: #155724; margin: 0 0 10px 0;">Import Successful!</h4>
        <p id="excelSuccessMessage" style="margin: 0;"></p>
      </div>

      <div style="text-align: right; margin-top: 20px;">
        <button class="btn btn-outline btn-cancel" style="margin-right: 10px;">Cancel</button>
        <button class="btn btn-primary btn-import-excel" disabled>Import Excel</button>
      </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // Event handlers
    const cancelBtn = modal.querySelector(".btn-cancel");
    const importBtn = modal.querySelector(".btn-import-excel");
    const fileInput = modal.querySelector("#excelFile");

    cancelBtn.addEventListener("click", () => {
      document.body.removeChild(modal);
    });

    fileInput.addEventListener("change", (e) => {
      importBtn.disabled = !e.target.files[0];
    });

    importBtn.addEventListener("click", () => {
      const file = fileInput.files[0];
      if (file) {
        handleExcelImport(file, modal, importBtn);
      }
    });
  }

  // CSV Import Handler
  function handleCsvImport(file, modal, importBtn) {
    const formData = new FormData();
    formData.append("csv_file", file);
    formData.append(
      "csrfmiddlewaretoken",
      document.querySelector("[name=csrfmiddlewaretoken]").value
    );

    // Show loading state
    const originalText = importBtn.innerHTML;
    importBtn.innerHTML =
      '<i class="bx bx-loader-alt bx-spin"></i> Importing...';
    importBtn.disabled = true;

    fetch("/dashboard/attendance/import-csv/", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        // Reset button
        importBtn.innerHTML = originalText;
        importBtn.disabled = false;

        if (data.success) {
          // Show success message
          const successDiv = modal.querySelector("#importSuccess");
          const successMessage = modal.querySelector("#successMessage");
          successMessage.textContent = `Successfully imported ${data.imported_count} attendance records. Data is now in pending state - please use "Commit Attendance" to finalize.`;
          successDiv.style.display = "block";

          // Show errors if any
          if (data.errors && data.errors.length > 0) {
            const errorsDiv = modal.querySelector("#importErrors");
            const errorsList = modal.querySelector("#errorsList");
            errorsList.innerHTML = data.errors
              .map((error) => `<div>${error}</div>`)
              .join("");
            errorsDiv.style.display = "block";
          }

          // Auto refresh after 3 seconds
          setTimeout(() => {
            location.reload();
          }, 3000);
        } else {
          // Show error
          const errorsDiv = modal.querySelector("#importErrors");
          const errorsList = modal.querySelector("#errorsList");
          errorsList.innerHTML = `<div>${data.error}</div>`;
          errorsDiv.style.display = "block";
        }
      })
      .catch((error) => {
        // Reset button
        importBtn.innerHTML = originalText;
        importBtn.disabled = false;

        // Show error
        const errorsDiv = modal.querySelector("#importErrors");
        const errorsList = modal.querySelector("#errorsList");
        errorsList.innerHTML = `<div>Import failed: ${error.message}</div>`;
        errorsDiv.style.display = "block";
      });
  }

  // Excel Import Handler
  function handleExcelImport(file, modal, importBtn) {
    const formData = new FormData();
    formData.append("excel_file", file);
    formData.append(
      "csrfmiddlewaretoken",
      document.querySelector("[name=csrfmiddlewaretoken]").value
    );

    // Show loading state
    const originalText = importBtn.innerHTML;
    importBtn.innerHTML =
      '<i class="bx bx-loader-alt bx-spin"></i> Importing...';
    importBtn.disabled = true;

    fetch("/dashboard/attendance/import-excel/", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        // Reset button
        importBtn.innerHTML = originalText;
        importBtn.disabled = false;

        if (data.success) {
          // Show success message
          const successDiv = modal.querySelector("#excelImportSuccess");
          const successMessage = modal.querySelector("#excelSuccessMessage");
          successMessage.textContent = `Successfully imported ${data.imported_count} attendance records. Data is now in pending state - please use "Commit Attendance" to finalize.`;
          successDiv.style.display = "block";

          // Show errors if any
          if (data.errors && data.errors.length > 0) {
            const errorsDiv = modal.querySelector("#excelImportErrors");
            const errorsList = modal.querySelector("#excelErrorsList");
            errorsList.innerHTML = data.errors
              .map((error) => `<div>${error}</div>`)
              .join("");
            errorsDiv.style.display = "block";
          }

          // Auto refresh after 3 seconds
          setTimeout(() => {
            location.reload();
          }, 3000);
        } else {
          // Show error
          const errorsDiv = modal.querySelector("#excelImportErrors");
          const errorsList = modal.querySelector("#excelErrorsList");
          errorsList.innerHTML = `<div>${data.error}</div>`;
          errorsDiv.style.display = "block";
        }
      })
      .catch((error) => {
        // Reset button
        importBtn.innerHTML = originalText;
        importBtn.disabled = false;

        // Show error
        const errorsDiv = modal.querySelector("#excelImportErrors");
        const errorsList = modal.querySelector("#excelErrorsList");
        errorsList.innerHTML = `<div>Import failed: ${error.message}</div>`;
        errorsDiv.style.display = "block";
      });
  }

  // Teacher CSV Export Handler (direct export for current date)
  function handleTeacherCsvExport() {
    const today = new Date().toISOString().split("T")[0]; // Get current date in YYYY-MM-DD format
    const url = `/dashboard/attendance/export-csv/?from_date=${today}`;
    window.open(url, "_blank");
  }

  // CSV Export Handler (modal for admin)
  function handleCsvExport() {
    const modal = document.createElement("div");
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); display: flex; align-items: center;
      justify-content: center; z-index: 1000;
    `;

    const modalContent = document.createElement("div");
    modalContent.style.cssText = `
      background: white; padding: 20px; border-radius: 8px;
      min-width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;

    modalContent.innerHTML = `
      <h3>Export Attendance Data</h3>
      <div style="margin: 15px 0;">
        <label for="fromDate">Export From Date:</label><br>
        <input type="date" id="fromDate" style="width: 100%; padding: 8px; margin: 5px 0;">
        <small style="color: #666;">Leave empty to export all attendance data</small>
      </div>
      <div style="text-align: right; margin-top: 20px;">
        <button class="btn btn-outline btn-cancel" style="margin-right: 10px;">Cancel</button>
        <button class="btn btn-primary btn-export">Export</button>
      </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    const exportBtn = modal.querySelector(".btn-export");
    const cancelBtn = modal.querySelector(".btn-cancel");

    cancelBtn.addEventListener("click", () => {
      document.body.removeChild(modal);
    });

    exportBtn.addEventListener("click", () => {
      const fromDate = modal.querySelector("#fromDate").value;

      // Build URL with parameters
      let url = "/dashboard/attendance/export-csv/?";
      const params = [];
      if (fromDate) params.push(`from_date=${fromDate}`);
      url += params.join("&");

      // Start download
      window.open(url, "_blank");
      document.body.removeChild(modal);
    });
  }

  // Teacher Excel Export Handler (direct export for current date)
  function handleTeacherExcelExport() {
    const today = new Date().toISOString().split("T")[0]; // Get current date in YYYY-MM-DD format
    const url = `/dashboard/attendance/export-excel/?from_date=${today}`;
    window.open(url, "_blank");
  }

  // Excel Export Handler (modal for admin)
  function handleExcelExport() {
    const modal = document.createElement("div");
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); display: flex; align-items: center;
      justify-content: center; z-index: 1000;
    `;

    const modalContent = document.createElement("div");
    modalContent.style.cssText = `
      background: white; padding: 20px; border-radius: 8px;
      min-width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;

    modalContent.innerHTML = `
      <h3>Export Attendance Data to Excel</h3>
      <div style="margin: 15px 0;">
        <label for="fromDate">Export From Date:</label><br>
        <input type="date" id="fromDate" style="width: 100%; padding: 8px; margin: 5px 0;">
        <small style="color: #666;">Leave empty to export all attendance data</small>
      </div>
      <div style="text-align: right; margin-top: 20px;">
        <button class="btn btn-outline btn-cancel" style="margin-right: 10px;">Cancel</button>
        <button class="btn btn-primary btn-export">Export Excel</button>
      </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    const exportBtn = modal.querySelector(".btn-export");
    const cancelBtn = modal.querySelector(".btn-cancel");

    cancelBtn.addEventListener("click", () => {
      document.body.removeChild(modal);
    });

    exportBtn.addEventListener("click", () => {
      const fromDate = modal.querySelector("#fromDate").value;

      // Build URL with parameters
      let url = "/dashboard/attendance/export-excel/?";
      const params = [];
      if (fromDate) params.push(`from_date=${fromDate}`);
      url += params.join("&");

      // Start download
      window.open(url, "_blank");
      document.body.removeChild(modal);
    });
  }

  // Teacher JSON Export Handler (direct export for current date)
  function handleTeacherJsonExport() {
    const today = new Date().toISOString().split("T")[0]; // Get current date in YYYY-MM-DD format
    const url = `/dashboard/attendance/export-json/?from_date=${today}`;
    window.open(url, "_blank");
  }

  // JSON Export Handler (modal for admin)
  function handleJsonExport() {
    const modal = document.createElement("div");
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); display: flex; align-items: center;
      justify-content: center; z-index: 1000;
    `;

    const modalContent = document.createElement("div");
    modalContent.style.cssText = `
      background: white; padding: 20px; border-radius: 8px;
      min-width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;

    modalContent.innerHTML = `
      <h3>Export Attendance Data to JSON</h3>
      <div style="margin: 15px 0;">
        <label for="fromDate">Export From Date:</label><br>
        <input type="date" id="fromDate" style="width: 100%; padding: 8px; margin: 5px 0;">
        <small style="color: #666;">Leave empty to export all attendance data</small>
      </div>
      <div style="text-align: right; margin-top: 20px;">
        <button class="btn btn-outline btn-cancel" style="margin-right: 10px;">Cancel</button>
        <button class="btn btn-primary btn-export">Export JSON</button>
      </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    const exportBtn = modal.querySelector(".btn-export");
    const cancelBtn = modal.querySelector(".btn-cancel");

    cancelBtn.addEventListener("click", () => {
      document.body.removeChild(modal);
    });

    exportBtn.addEventListener("click", () => {
      const fromDate = modal.querySelector("#fromDate").value;

      // Build URL with parameters
      let url = "/dashboard/attendance/export-json/?";
      const params = [];
      if (fromDate) params.push(`from_date=${fromDate}`);
      url += params.join("&");

      // Start download
      window.open(url, "_blank");
      document.body.removeChild(modal);
    });
  }
});
