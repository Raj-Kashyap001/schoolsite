// Model Functionality
let modal = document.getElementById("applyLeaveModal");
let btn = document.getElementById("applyLeaveBtn");
let span = document.getElementsByClassName("close")[0];

btn.onclick = function () {
  modal.style.display = "block";
};

span.onclick = function () {
  modal.style.display = "none";
};

window.onclick = function (event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
};

// Form submission
document
  .getElementById("applyLeaveForm")
  .addEventListener("submit", function (e) {
    e.preventDefault();
    const formData = new FormData(this);
    // Ensure CSRF token is included
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) {
      formData.append("csrfmiddlewaretoken", csrfToken.value);
    }
    fetch(leaveUrl, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
    })
      .then((response) => {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          return response.json();
        } else {
          throw new Error(
            "Server returned non-JSON response. Please check your login session."
          );
        }
      })
      .then((data) => {
        if (data.success) {
          location.reload();
        } else {
          alert("Error: " + data.error);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred: " + error.message);
      });
  });

// Edit and Delete buttons
document.querySelectorAll(".edit-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    const leaveId = this.getAttribute("data-id");
    // Fetch leave data and populate modal
    fetch(`${leaveUrl}?action=get&leave_id=${leaveId}`, {
      credentials: "same-origin",
    })
      .then((response) => {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          return response.json();
        } else {
          throw new Error(
            "Server returned non-JSON response. Please check your login session."
          );
        }
      })
      .then((data) => {
        if (data.success) {
          document.getElementById("reason").value = data.leave.reason;
          document.getElementById("from_date").value = data.leave.from_date;
          document.getElementById("to_date").value = data.leave.to_date;
          // Add hidden inputs for edit
          const form = document.getElementById("applyLeaveForm");
          form.insertAdjacentHTML(
            "beforeend",
            `<input type="hidden" name="action" value="edit" id="actionInput"><input type="hidden" name="leave_id" value="${leaveId}" id="leaveIdInput">`
          );
          modal.style.display = "block";
        } else {
          alert("Error: " + data.error);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred: " + error.message);
      });
  });
});

document.querySelectorAll(".delete-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    if (confirm("Are you sure you want to delete this leave request?")) {
      const leaveId = this.getAttribute("data-id");
      const formData = new FormData();
      formData.append("action", "delete");
      formData.append("leave_id", leaveId);
      // Add CSRF token
      const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
      if (csrfToken) {
        formData.append("csrfmiddlewaretoken", csrfToken.value);
      }
      fetch(leaveUrl, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
      })
        .then((response) => {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            return response.json();
          } else {
            throw new Error(
              "Server returned non-JSON response. Please check your login session."
            );
          }
        })
        .then((data) => {
          if (data.success) {
            location.reload();
          } else {
            alert("Error: " + data.error);
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("An error occurred: " + error.message);
        });
    }
  });
});

// Admin approve/reject functionality
document.querySelectorAll(".approve-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    const leaveId = this.getAttribute("data-id");
    if (confirm("Are you sure you want to approve this leave request?")) {
      const formData = new FormData();
      formData.append("action", "approve");
      formData.append("leave_id", leaveId);
      // Add CSRF token
      const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
      if (csrfToken) {
        formData.append("csrfmiddlewaretoken", csrfToken.value);
      }
      fetch(leaveUrl, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
      })
        .then((response) => {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            return response.json();
          } else {
            throw new Error(
              "Server returned non-JSON response. Please check your login session."
            );
          }
        })
        .then((data) => {
          if (data.success) {
            location.reload();
          } else {
            alert("Error: " + (data.error || "Unknown error"));
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("An error occurred: " + error.message);
        });
    }
  });
});

document.querySelectorAll(".reject-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    const leaveId = this.getAttribute("data-id");
    if (confirm("Are you sure you want to reject this leave request?")) {
      const formData = new FormData();
      formData.append("action", "reject");
      formData.append("leave_id", leaveId);
      // Add CSRF token
      const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
      if (csrfToken) {
        formData.append("csrfmiddlewaretoken", csrfToken.value);
      }
      fetch(leaveUrl, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
      })
        .then((response) => {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            return response.json();
          } else {
            throw new Error(
              "Server returned non-JSON response. Please check your login session."
            );
          }
        })
        .then((data) => {
          if (data.success) {
            location.reload();
          } else {
            alert("Error: " + (data.error || "Unknown error"));
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("An error occurred: " + error.message);
        });
    }
  });
});

// Reset form when modal opens for new leave
btn.onclick = function () {
  // Remove edit hidden inputs if exist
  const actionInput = document.getElementById("actionInput");
  const leaveIdInput = document.getElementById("leaveIdInput");
  if (actionInput) actionInput.remove();
  if (leaveIdInput) leaveIdInput.remove();
  // Reset form
  document.getElementById("applyLeaveForm").reset();
  modal.style.display = "block";
};
