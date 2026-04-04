const tabsContainer = document.querySelectorAll(".tabs");
if (tabsContainer.length) {
  tabsContainer.forEach((container) => {
    const buttons = container.querySelectorAll("[name=tab-btn]");
    const contents = container.querySelectorAll("[id*=content-]");
    if (buttons) {
      buttons.forEach((btn) => {
        const containerNumber = Number(
          btn.getAttribute("id").replace("tab-btn-", "")
        );
        if (btn.checked) {
          contents[containerNumber - 1].classList.add("active");
        }
        btn.addEventListener("click", () => {
          const containerNumber = Number(
            btn.getAttribute("id").replace("tab-btn-", "")
          );
          contents.forEach((content) =>
            content.classList.contains("active")
              ? content.classList.remove("active")
              : 0
          );
          contents[containerNumber - 1].classList.add("active");
        });
      });
    }
  });
}
