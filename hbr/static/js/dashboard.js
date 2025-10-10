// Sidebar toggle functionality
const sidebarToggleMobile = document.getElementById("sidebarToggleMobile");
const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");
const sidebar = document.querySelector(".sidebar");

if (sidebarToggleMobile && sidebar && sidebarCloseBtn) {
  sidebarToggleMobile.addEventListener("click", () => {
    sidebar.classList.add("active");
  });

  sidebarCloseBtn.addEventListener("click", () => {
    sidebar.classList.remove("active");
  });
}

// Notification dropdown functionality
const notificationToggle = document.getElementById("notificationToggle");
const notificationDropdown = document.getElementById("notificationDropdown");

if (notificationToggle && notificationDropdown) {
  notificationToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    notificationDropdown.classList.toggle("show");
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (
      !notificationDropdown.contains(e.target) &&
      !notificationToggle.contains(e.target)
    ) {
      notificationDropdown.classList.remove("show");
    }
  });

  // Close dropdown on escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      notificationDropdown.classList.remove("show");
    }
  });
}
