// CHATGPT: render ISO dates as Solar Hijri dates and filter same-month recommendations using the Persian calendar.
(() => {
  const options = { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" };
  const formatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", options);
  const solarMonth = (isoDate) => {
    const date = new Date(isoDate + "T12:00:00Z");
    if (Number.isNaN(date.getTime())) return null;
    const parts = formatter.formatToParts(date);
    return {
      year: parts.find((part) => part.type === "year")?.value,
      month: parts.find((part) => part.type === "month")?.value
    };
  };

  document.querySelectorAll(".js-local-date[data-date]").forEach((node) => {
    const date = new Date(node.dataset.date + "T12:00:00Z");
    if (!Number.isNaN(date.getTime())) node.textContent = formatter.format(date);
  });

  const solarDateParts = (isoDate) => {
    const date = new Date(isoDate + "T12:00:00Z");
    if (Number.isNaN(date.getTime())) return null;
    const parts = formatter.formatToParts(date);
    const numeric = (type) => Number(parts.find((part) => part.type === type)?.value.replace(/[^0-9]/g, ""));
    return { year: numeric("year"), month: parts.find((part) => part.type === "month")?.value, day: numeric("day") };
  };

  document.querySelectorAll(".same-day-years[data-current-date]").forEach((group) => {
    const current = solarDateParts(group.dataset.currentDate);
    if (!current) return;
    let visible = 0;
    group.querySelectorAll("li time[data-date]").forEach((time) => {
      const past = solarDateParts(time.dataset.date);
      const matches = past && past.month === current.month && past.day === current.day && past.year < current.year;
      time.closest("li").hidden = !matches;
      const label = time.closest("li").querySelector(".years-ago");
      if (label && matches) label.textContent = `${current.year - past.year} سال پیش`;
      if (matches) visible += 1;
    });
    group.hidden = visible === 0;
  });

  document.querySelectorAll(".related-posts[data-current-date]").forEach((related) => {
    const current = solarMonth(related.dataset.currentDate);
    if (!current) return;
    related.querySelectorAll(".related-group").forEach((group) => {
      const heading = group.querySelector("h3");
      if (!heading || heading.textContent.trim() !== "در همین ماه") return;
      let visible = 0;
      group.querySelectorAll("li time[data-date]").forEach((time) => {
        const itemMonth = solarMonth(time.dataset.date);
        const sameMonth = itemMonth && itemMonth.year === current.year && itemMonth.month === current.month;
        time.closest("li").hidden = !sameMonth;
        if (sameMonth) visible += 1;
      });
      group.hidden = visible === 0;
    });
  });
})();
