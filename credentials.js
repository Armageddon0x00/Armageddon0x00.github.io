const credentialVerifications = Object.freeze({
  oscp: [
    {
      name: "OSCP",
      label: "OSCP",
      url: "https://credentials.offsec.com/4371e9da-8cab-4d47-adef-5d74b97c41ef#acc.bKaj8lAk",
    },
    {
      name: "OSCP+",
      label: "OSCP+",
      url: "https://credentials.offsec.com/314f62a5-21c9-4185-92a1-07ae42d4a70e#acc.cTBkP9d7",
    },
  ],
  ecppt: [
    {
      name: "eCPPT",
      label: "Verify",
      url: "https://certs.ine.com/54b0f4eb-19d4-4e68-970d-21fd6b3c8bd5#acc.1LECvtWF",
    },
  ],
  emapt: [
    {
      name: "eMAPT",
      label: "Verify",
      url: "https://certs.ine.com/eb08fa7f-7ffd-40ce-928e-65afd42d71de#acc.gHu5JVf0",
    },
  ],
  ewptx: [
    {
      name: "eWPTXv2",
      label: "Verify",
      url: "https://certs.ine.com/7aa19595-e6fa-4063-9407-d2677e9bcd7f#acc.KCaYoOLV",
    },
  ],
  pentest: [
    {
      name: "CompTIA PenTest+",
      label: "Verify",
      url: "https://www.credly.com/badges/97ae7b10-fa6a-424c-a1f9-8c24acdb8270/public_url",
    },
  ],
  cysa: [
    {
      name: "CompTIA CySA+",
      label: "Verify",
      url: "https://www.credly.com/badges/0678fae7-c3e1-469c-986f-349641dc9003/public_url",
    },
  ],
  security: [
    {
      name: "CompTIA Security+",
      label: "Verify",
      url: "https://www.credly.com/badges/e9da249b-28f3-480d-8caa-81153d51b691/public_url",
    },
  ],
  network: [
    {
      name: "CompTIA Network+",
      label: "Verify",
      url: "https://www.credly.com/badges/5d6c6730-f8b2-4c18-935e-e06e6f1ef9c5/public_url",
    },
  ],
});

const stackableVerifications = Object.freeze([
  {
    name: "CompTIA Network Security Professional",
    label: "CNSP",
    url: "https://www.credly.com/badges/ef4c911c-2a0d-48b8-a843-c7a80c7f101b",
  },
  {
    name: "CompTIA Security Analytics Professional",
    label: "CSAP",
    url: "https://www.credly.com/badges/e5625f7b-f7d1-44df-aa4a-e52e1bac8563",
  },
  {
    name: "CompTIA Network Vulnerability Assessment Professional",
    label: "CNVP",
    url: "https://www.credly.com/badges/ba75d707-f4fc-408a-a952-7a7174661491",
  },
]);

const createVerificationLink = ({ name, label, url }, className) => {
  const link = document.createElement("a");
  link.className = className;
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.setAttribute("aria-label", `Verify ${name} (opens in a new tab)`);

  const text = document.createElement("span");
  text.textContent = label;
  link.append(text);

  const arrow = document.createElement("span");
  arrow.setAttribute("aria-hidden", "true");
  arrow.textContent = "↗";
  link.append(arrow);

  return link;
};

document.querySelectorAll("[data-credential]").forEach((card) => {
  const key = card.dataset.credential;
  const destination = card.querySelector("[data-credential-verifications]");
  const verifications = credentialVerifications[key];

  if (!destination || !verifications) {
    console.error(`Missing verification configuration for credential: ${key || "unknown"}`);
    return;
  }

  destination.replaceChildren(
    ...verifications.map((verification) =>
      createVerificationLink(verification, "certification-verify")
    )
  );
});

const stackableDestination = document.querySelector("[data-stackable-verifications]");

if (stackableDestination) {
  const label = document.createElement("span");
  label.className = "stackable-label";
  label.textContent = "Stackables";

  stackableDestination.replaceChildren(
    label,
    ...stackableVerifications.map((verification) =>
      createVerificationLink(verification, "stackable-verify")
    )
  );
}
