const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const progress = document.querySelector(".scroll-progress");
const portrait = document.querySelector("[data-portrait]");
const revealElements = document.querySelectorAll("[data-reveal]");
const snapSections = [
  ...document.querySelectorAll(
    ".ataturk-hero, .republic, .archive, .ataturk-closing-page"
  ),
];

let snapInProgress = false;
let snapReleaseTimer;

const snapToSection = (index) => {
  const section = snapSections[index];
  if (!section) return;

  snapInProgress = true;
  section.scrollIntoView({
    behavior: reducedMotion.matches ? "auto" : "smooth",
    block: "start",
  });

  window.clearTimeout(snapReleaseTimer);
  snapReleaseTimer = window.setTimeout(() => {
    snapInProgress = false;
  }, 900);
};

if (!reducedMotion.matches) {
  window.addEventListener(
    "wheel",
    (event) => {
      if (event.ctrlKey || document.querySelector("#archive-lightbox")?.open) return;

      if (snapInProgress) {
        event.preventDefault();
        return;
      }

      const direction = Math.sign(event.deltaY);
      if (direction === 0) return;

      const scrollPosition = window.scrollY;
      const viewportHeight = window.innerHeight;
      const activeIndex = snapSections.findIndex((section) => {
        const top = section.offsetTop;
        const bottom = top + section.offsetHeight;
        return scrollPosition >= top - 2 && scrollPosition < bottom - 2;
      });

      if (activeIndex === -1) return;

      const activeSection = snapSections[activeIndex];
      const sectionTop = activeSection.offsetTop;
      const sectionBottom = sectionTop + activeSection.offsetHeight - viewportHeight;
      const hasInternalScroll = activeSection.offsetHeight > viewportHeight + 2;

      if (hasInternalScroll) {
        const atStart = scrollPosition <= sectionTop + 2;
        const atEnd = scrollPosition >= sectionBottom - 2;

        if ((direction > 0 && !atEnd) || (direction < 0 && !atStart)) return;
      }

      const targetIndex = activeIndex + direction;
      if (!snapSections[targetIndex]) return;

      event.preventDefault();
      snapToSection(targetIndex);
    },
    { passive: false }
  );
}

const updateScrollProgress = () => {
  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  const value = scrollable > 0 ? window.scrollY / scrollable : 0;
  progress?.style.setProperty("--scroll-progress", String(value));
};

updateScrollProgress();
window.addEventListener("scroll", updateScrollProgress, { passive: true });

if (reducedMotion.matches || !("IntersectionObserver" in window)) {
  revealElements.forEach((element) => element.classList.add("is-visible"));
} else {
  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.12 }
  );

  revealElements.forEach((element) => revealObserver.observe(element));
}

if (portrait && !reducedMotion.matches) {
  window.addEventListener(
    "pointermove",
    (event) => {
      const x = (event.clientX / window.innerWidth - 0.5) * 10;
      const y = (event.clientY / window.innerHeight - 0.5) * 10;
      portrait.style.setProperty("--portrait-x", x.toFixed(2));
      portrait.style.setProperty("--portrait-y", y.toFixed(2));
    },
    { passive: true }
  );
}

const archiveTrack = document.querySelector("[data-archive-track]");
const archiveSequence = document.querySelector("[data-archive-sequence]");
const galleryItems = [
  ...(archiveSequence?.querySelectorAll("[data-gallery-item]") ?? []),
];

galleryItems.forEach((item, index) => {
  item.dataset.galleryIndex = String(index);
});

if (archiveTrack && archiveSequence) {
  const ribbonCopy = archiveSequence.cloneNode(true);
  ribbonCopy.removeAttribute("data-archive-sequence");
  ribbonCopy.setAttribute("aria-hidden", "true");

  ribbonCopy.querySelectorAll("[data-gallery-item]").forEach((item) => {
    item.tabIndex = -1;
    item.removeAttribute("data-reveal");
    item.classList.add("is-visible");
  });

  archiveTrack.append(ribbonCopy);
}

const galleryTriggers = [...document.querySelectorAll("[data-gallery-item]")];
const lightbox = document.querySelector("#archive-lightbox");
const lightboxImage = lightbox?.querySelector("[data-lightbox-image]");
const lightboxNumber = lightbox?.querySelector("[data-lightbox-number]");
const lightboxCaption = lightbox?.querySelector("[data-lightbox-caption]");
let activeIndex = 0;

const showImage = (index) => {
  if (!lightbox || !lightboxImage || !lightboxNumber || !lightboxCaption) return;

  activeIndex = (index + galleryItems.length) % galleryItems.length;
  const item = galleryItems[activeIndex];
  const thumbnail = item.querySelector("img");

  lightboxImage.src = item.dataset.src ?? "";
  lightboxImage.alt = thumbnail?.alt ?? "";
  lightboxNumber.textContent = String(activeIndex + 1).padStart(2, "0");
  lightboxCaption.textContent = item.dataset.caption ?? "Arşiv";
};

galleryTriggers.forEach((item) => {
  item.addEventListener("click", () => {
    if (!lightbox) return;
    showImage(Number(item.dataset.galleryIndex ?? 0));
    lightbox.showModal();
    document.body.classList.add("lightbox-open");
  });
});

lightbox?.querySelector("[data-lightbox-close]")?.addEventListener("click", () => lightbox.close());
lightbox?.querySelector("[data-lightbox-prev]")?.addEventListener("click", () => showImage(activeIndex - 1));
lightbox?.querySelector("[data-lightbox-next]")?.addEventListener("click", () => showImage(activeIndex + 1));

lightbox?.addEventListener("click", (event) => {
  if (event.target === lightbox) lightbox.close();
});

lightbox?.addEventListener("close", () => {
  document.body.classList.remove("lightbox-open");
  lightboxImage?.removeAttribute("src");
});

document.addEventListener("keydown", (event) => {
  if (!lightbox?.open) return;
  if (event.key === "ArrowLeft") showImage(activeIndex - 1);
  if (event.key === "ArrowRight") showImage(activeIndex + 1);
});
