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

const closingScene = document.querySelector("[data-closing-scene]");
const pennantCurtain = document.querySelector("[data-pennant-curtain]");
const standardFields = document.querySelectorAll("[data-standard-field]");

const appendFlagEmblem = (flag) => {
  const crescent = document.createElement("span");
  const star = document.createElement("span");

  crescent.className = "flag-crescent";
  star.className = "flag-star";
  star.textContent = "★";
  flag.append(crescent, star);
};

if (pennantCurtain) {
  const pennantDrops = [6.4, 8.6, 7.2, 10.2, 8, 11.4, 9, 11.4, 8, 10.2, 7.2, 8.6, 6.4];

  pennantDrops.forEach((drop, index) => {
    const pennant = document.createElement("span");
    pennant.className = "ceremony-pennant";
    pennant.style.setProperty("--drop", `${drop}rem`);
    pennant.style.setProperty("--delay", `${0.08 + index * 0.055}s`);
    pennant.style.setProperty("--tilt", `${index % 2 === 0 ? -1.5 : 1.5}deg`);
    appendFlagEmblem(pennant);
    pennantCurtain.append(pennant);
  });
}

const standardProfiles = [
  { x: -5, pole: 43, scale: 0.68, angle: 39 },
  { x: 0, pole: 48, scale: 0.75, angle: 35 },
  { x: 6, pole: 53, scale: 0.82, angle: 31 },
  { x: 12, pole: 58, scale: 0.9, angle: 28 },
  { x: 18, pole: 64, scale: 0.98, angle: 25 },
  { x: 24, pole: 69, scale: 1.06, angle: 22 },
  { x: 30, pole: 74, scale: 1.14, angle: 19 },
  { x: 36, pole: 79, scale: 1.22, angle: 16 },
];

standardFields.forEach((field) => {
  const side = field.dataset.standardField;

  standardProfiles.forEach((profile, index) => {
    const standard = document.createElement("span");
    const pole = document.createElement("span");
    const flag = document.createElement("span");
    const direction = side === "left" ? 1 : -1;

    standard.className = "battle-standard";
    pole.className = "standard-pole";
    flag.className = "standard-flag";
    standard.style.setProperty("--x", `${profile.x}%`);
    standard.style.setProperty("--pole", `${profile.pole}vh`);
    standard.style.setProperty("--flag-scale", String(profile.scale));
    standard.style.setProperty("--angle", `${profile.angle * direction}deg`);
    standard.style.setProperty("--delay", `${0.24 + index * 0.09}s`);
    standard.style.setProperty("--wave-delay", `${-index * 0.22}s`);

    appendFlagEmblem(flag);
    standard.append(pole, flag);
    field.append(standard);
  });
});

if (closingScene) {
  if (reducedMotion.matches || !("IntersectionObserver" in window)) {
    closingScene.classList.add("is-active");
  } else {
    const ceremonyObserver = new IntersectionObserver(
      ([entry]) => {
        closingScene.classList.toggle("is-active", entry.isIntersecting);
      },
      { threshold: 0.28 }
    );

    ceremonyObserver.observe(closingScene);
  }
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
