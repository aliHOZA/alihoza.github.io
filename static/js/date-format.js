// CHATGPT: render ISO dates as Solar Hijri dates in Persian; keep machine-readable datetime unchanged.
(() => {
  const formatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" });
  document.querySelectorAll(".js-local-date[data-date]").forEach((node) => {
    const date = new Date(node.dataset.date + "T12:00:00Z");
    if (!Number.isNaN(date.getTime())) node.textContent = formatter.format(date);
  });
})();
