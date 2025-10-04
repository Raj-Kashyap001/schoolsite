document.addEventListener("DOMContentLoaded", function () {
  const changePhotoBtn = document.getElementById("change-photo-btn");
  const photoInput = document.getElementById("profile-photo-input");

  if (changePhotoBtn && photoInput) {
    changePhotoBtn.addEventListener("click", function (e) {
      e.preventDefault();
      photoInput.click();
    });

    photoInput.addEventListener("change", function () {
      const file = this.files[0];
      if (file) {
        // Validate file type
        if (!file.type.startsWith("image/")) {
          alert("Please select a valid image file.");
          return;
        }

        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
          alert("File size must be less than 5MB.");
          return;
        }

        // Show loading state
        //changePhotoBtn.disabled = true;
        //changePhotoBtn.innerHTML =
        // '<i class="bx bx-loader-alt bx-spin"></i> Uploading...';

        // Create FormData
        const formData = new FormData();
        formData.append("profile_photo", file);
        formData.append(
          "csrfmiddlewaretoken",
          document.querySelector("[name=csrfmiddlewaretoken]").value
        );

        // Upload via AJAX
        fetch(window.profileUrl, {
          method: "POST",
          body: formData,
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              // Update the profile photo display
              const photoSection = document.querySelector(
                ".profile-photo-section"
              );
              if (photoSection) {
                photoSection.innerHTML = `
                    <img src="${data.photo_url}" alt="Profile Photo" class="profile-photo" style="width: 120px; object-fit: cover; display:block; object-position: center; aspect-ratio: 1; margin-bottom: 1rem;" />
                  `;
              }

              // Update button text
              changePhotoBtn.innerHTML =
                '<i class="bx bx-image-portrait"></i> Change Profile Image';

              // Show success message
              showMessage("Profile photo updated successfully!", "success");
            } else {
              showMessage(data.error || "Failed to upload photo.", "error");
            }
          })
          .catch((error) => {
            console.error("Upload error:", error);
            showMessage("Failed to upload photo. Please try again.", "error");
          })
          .finally(() => {
            changePhotoBtn.disabled = false;
          });
      }
    });
  }

  function showMessage(message, type) {
    // Create message element
    const messageEl = document.createElement("div");
    messageEl.className = `message ${type}`;
    messageEl.textContent = message;
    messageEl.style.cssText = `
          position: fixed;
          bottom: 20px;
          right: 20px;
          padding: 1rem 1.5rem;
          border-radius: 8px;
          color: white;
          font-weight: 500;
          z-index: 1000;
          animation: slideIn 0.3s ease;
        `;

    if (type === "success") {
      messageEl.style.backgroundColor = "#10b981";
    } else {
      messageEl.style.backgroundColor = "#ef4444";
    }

    document.body.appendChild(messageEl);

    // Remove after 3 seconds
    setTimeout(() => {
      messageEl.style.animation = "slideOut 0.3s ease";
      setTimeout(() => {
        document.body.removeChild(messageEl);
      }, 300);
    }, 3000);
  }
});

// Add CSS animations
const style = document.createElement("style");
style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
      .bx-spin {
        animation: spin 1s linear infinite;
      }
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;
document.head.appendChild(style);
