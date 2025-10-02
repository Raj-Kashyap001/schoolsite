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
    fetch(leaveUrl, {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
          .value,
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          location.reload();
        } else {
          alert("Error: " + data.error);
        }
      });
  });

// Edit and Delete buttons
document.querySelectorAll(".edit-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    const leaveId = this.getAttribute("data-id");
    // Fetch leave data and populate modal
    fetch(`${leaveUrl}?action=get&leave_id=${leaveId}`)
      .then((response) => response.json())
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
        }
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
      fetch(leaveUrl, {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            location.reload();
          } else {
            alert("Error: " + data.error);
          }
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
