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

  const toLatinDigits = (value) => value.replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)));
  const solarDateParts = (isoDate) => {
    const date = new Date(isoDate + "T12:00:00Z");
    if (Number.isNaN(date.getTime())) return null;
    const parts = formatter.formatToParts(date);
    const numeric = (type) => Number(toLatinDigits(parts.find((part) => part.type === type)?.value || ""));
    return { year: numeric("year"), month: parts.find((part) => part.type === "month")?.value, day: numeric("day") };
  };

  const related = document.querySelector(".related-posts[data-current-date]");
  if (related) {
    const current = solarDateParts(related.dataset.currentDate);
    if (current) {
      const shown = new Set();
      const groups = Array.from(related.querySelectorAll(".related-group"));
      const dayGroup = groups.find((group) => group.classList.contains("same-day-years"));
      const monthGroup = groups.find((group) => {
        const heading = group.querySelector("h3");
        return heading && heading.textContent.trim() === "در همین ماه";
      });

      const revealMatching = (group, matchesDate, limit = 4) => {
        if (!group) return;
        let visible = 0;
        group.querySelectorAll("li").forEach((item) => {
          const time = item.querySelector("time[data-date]");
          const date = time ? solarDateParts(time.dataset.date) : null;
          const href = item.querySelector("a")?.getAttribute("href");
          const matches = Boolean(date && matchesDate(date) && href && !shown.has(href));
          if (matches && visible < limit) {
            item.hidden = false;
            shown.add(href);
            visible += 1;
            const label = item.querySelector(".years-ago");
            if (label) label.textContent = `${current.year - date.year} سال قبل`;
          } else {
            item.hidden = true;
          }
        });
        group.hidden = visible === 0;
      };

      revealMatching(dayGroup, (date) =>
        date.year < current.year && date.month === current.month && date.day === current.day
      );
      revealMatching(monthGroup, (date) =>
        date.year < current.year && date.month === current.month
      );

      // Avoid repeating the anniversary/month selections in the later recommendation groups.
      let seenCount = 0;
      groups.forEach((group) => {
        if (group === dayGroup || group === monthGroup || group.classList.contains("post-neighbor")) return;
        let visible = 0;
        group.querySelectorAll("li").forEach((item) => {
          const href = item.querySelector("a")?.getAttribute("href");
          if (href && shown.has(href)) {
            item.hidden = true;
          } else if (href && !item.hidden) {
            shown.add(href);
            visible += 1;
          } else if (!item.hidden) {
            visible += 1;
          }
        });
        if (group.querySelectorAll("li").length && visible === 0) group.hidden = true;
        seenCount += visible;
      });
    }
  }
})();
