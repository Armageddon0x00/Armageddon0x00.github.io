const year = document.querySelector("#year");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const certifications = document.querySelector("[data-certifications]");
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

const activateOnView = (section, threshold) => {
  if (!section) return;

  if (reducedMotion.matches || !("IntersectionObserver" in window)) {
    section.classList.add("is-active");
  } else {
    const sectionObserver = new IntersectionObserver(
      ([entry]) => {
        section.classList.toggle("is-active", entry.isIntersecting);
      },
      { threshold }
    );

    sectionObserver.observe(section);
  }
};

activateOnView(certifications, 0.25);
activateOnView(horsemen, 0.3);
