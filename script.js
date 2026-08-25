const year = document.querySelector("#year");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const horsemen = document.querySelector("[data-horsemen]");
const threatTrack = document.querySelector("[data-threat-track]");
const threatSequence = document.querySelector("[data-threat-sequence]");

if (year) {
  const currentYear = new Date().getFullYear();
  year.dateTime = String(currentYear);
  year.textContent = String(currentYear);
}

if (threatTrack && threatSequence) {
  const threatCopy = threatSequence.cloneNode(true);
  threatCopy.removeAttribute("data-threat-sequence");
  threatCopy.removeAttribute("role");
  threatCopy.setAttribute("aria-hidden", "true");
  threatTrack.append(threatCopy);
}

if (horsemen) {
  if (reducedMotion.matches || !("IntersectionObserver" in window)) {
    horsemen.classList.add("is-active");
  } else {
    const horsemenObserver = new IntersectionObserver(
      ([entry]) => {
        horsemen.classList.toggle("is-active", entry.isIntersecting);
      },
      { threshold: 0.3 }
    );

    horsemenObserver.observe(horsemen);
  }
}
