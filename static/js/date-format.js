// CHATGPT: format Persian-calendar dates and load compact same-day/month recommendations on demand.
(() => {
  const options = { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" };
  const formatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", options);
  const toLatinDigits = (value) => value.replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)));

  const dateObject = (isoDate) => {
    const date = new Date(String(isoDate || "") + "T12:00:00Z");
    return Number.isNaN(date.getTime()) ? null : date;
  };

  const solarDateParts = (isoDate) => {
    const date = dateObject(isoDate);
    if (!date) return null;
    const parts = formatter.formatToParts(date);
    const numeric = (type) => Number(toLatinDigits(parts.find((part) => part.type === type)?.value || ""));
    return {
      year: numeric("year"),
      month: parts.find((part) => part.type === "month")?.value,
      day: numeric("day")
    };
  };

  document.querySelectorAll(".js-local-date[data-date]").forEach((node) => {
    const date = dateObject(node.dataset.date);
    if (date) node.textContent = formatter.format(date);
  });

  const related = document.querySelector(".related-posts[data-current-date][data-date-index-url]");
  if (!related) return;

  const current = solarDateParts(related.dataset.currentDate);
  if (!current) return;

  const dayGroup = related.querySelector(".same-day-years");
  const monthGroup = related.querySelector(".same-month-posts");
  if (!dayGroup && !monthGroup) return;

  const shown = new Set([window.location.href, ...Array.from(related.querySelectorAll(".post-neighbor a"))
    .map((anchor) => {
      try { return new URL(anchor.href, window.location.origin).href; }
      catch { return ""; }
    }).filter(Boolean)]);

  const makeRecommendation = (post, date, includeYearsAgo = false) => {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = post.url;
    link.textContent = post.title || "بدون عنوان";
    item.append(link);

    if (includeYearsAgo) {
      const years = document.createElement("span");
      years.className = "years-ago";
      const difference = current.year - date.year;
      years.textContent = difference > 0 ? difference + " سال قبل" : Math.abs(difference) + " سال بعد";
      item.append(years);
    }

    const time = document.createElement("time");
    time.className = "js-local-date";
    time.dataset.date = post.date;
    time.dateTime = post.date;
    const value = dateObject(post.date);
    if (value) time.textContent = formatter.format(value);
    item.append(time);
    return item;
  };

  const appendMatches = (group, posts, matches, limit, includeYearsAgo = false, includeFutureYears = false) => {
    if (!group) return;
    const list = group.querySelector(".related-list");
    if (!list) return;
    list.replaceChildren();
    let count = 0;

    for (const post of posts) {
      if (count >= limit) break;
      const date = solarDateParts(post.date);
      if (!date || (includeFutureYears ? date.year === current.year : date.year >= current.year) || !matches(date)) continue;

      let url;
      try { url = new URL(post.url, window.location.origin).href; }
      catch { continue; }
      if (!url || shown.has(url)) continue;

      list.append(makeRecommendation(post, date, includeYearsAgo));
      shown.add(url);
      count += 1;
    }
    group.hidden = count === 0;
  };

  fetch(related.dataset.dateIndexUrl)
    .then((response) => {
      if (!response.ok) throw new Error("Date index request failed");
      return response.json();
    })
    .then((posts) => {
      if (!Array.isArray(posts)) throw new Error("Invalid date index");
      appendMatches(dayGroup, posts, (date) => date.month === current.month && date.day === current.day, 4, true, true);
      appendMatches(monthGroup, posts, (date) => date.month === current.month, 4);
    })
    .catch(() => {
      if (dayGroup) dayGroup.hidden = true;
      if (monthGroup) monthGroup.hidden = true;
    });
})();
