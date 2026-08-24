const year = document.querySelector("#year");

if (year) {
  const currentYear = new Date().getFullYear();
  year.dateTime = String(currentYear);
  year.textContent = String(currentYear);
}
