(() => {
  const form = document.getElementById("site-search");
  if (!form) return;

  const input = document.getElementById("search-query");
  // Allow keyword-cloud links to prefill and execute a full-text search.
  const initialQuery = new URLSearchParams(window.location.search).get("q");
  if (initialQuery) input.value = initialQuery;
  const status = document.getElementById("search-status");
  const results = document.getElementById("search-results");
  let pages = [];
  let indexedPages = [];

  const normalize = (value) => String(value || "")
    .toLocaleLowerCase("fa")
    .replace(/[يى]/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/[\u064B-\u065F\u0670\u0640]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const runSearch = () => {
    const query = normalize(input.value);
    results.replaceChildren();

    if (query.length < 2) {
      status.textContent = "برای جستجو دست‌کم دو نویسه وارد کنید.";
      return;
    }

    const terms = query.split(" ").filter(Boolean);
    const found = indexedPages.map((item) => {
      let score = 0;
      for (const term of terms) {
        if (item.title.includes(term)) score += 12;
        if (item.url.includes(term) || item.slug.includes(term) || item.virgoolId.includes(term) || item.originalUrl.includes(term)) score += 10;
        if (item.tags.includes(term)) score += 7;
        if (item.categories.includes(term)) score += 6;
        if (item.summary.includes(term)) score += 4;
        if (item.content.includes(term)) score += 1;
      }
      return { page: item.page, score, item };
    }).filter(({ score, item }) => score > 0 && terms.every((term) =>
      [item.title, item.url, item.slug, item.virgoolId, item.originalUrl, item.summary, item.content, item.tags, item.categories].some((field) => field.includes(term))
    )).sort((a, b) => b.score - a.score || b.page.date.localeCompare(a.page.date));

    const shown = found.slice(0, 50);
    status.textContent = found.length
      ? (found.length + " نتیجه پیدا شد" + (found.length > shown.length ? "؛ ۵۰ نتیجهٔ نخست نمایش داده شده‌اند." : ""))
      : "نتیجه‌ای پیدا نشد. عبارت دیگری را امتحان کنید.";

    for (const { page } of shown) {
      const article = make("article", "search-result");
      const heading = make("h2", "search-result-title");
      const link = make("a", "", page.title || "بدون عنوان");
      link.href = page.url;
      heading.append(link);
      article.append(heading);

      const date = page.date ? new Date(page.date + "T12:00:00Z") : null;
      const displayDate = date && !Number.isNaN(date.getTime())
        ? new Intl.DateTimeFormat("fa-IR-u-ca-persian", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }).format(date)
        : (page.date || "");
      const meta = make("div", "post-meta", displayDate);
      article.append(meta);

      if (page.summary) article.append(make("p", "post-summary", page.summary));

      const labels = [...(page.tags || []), ...(page.categories || [])].slice(0, 5);
      if (labels.length) {
        const chips = make("div", "tag-row");
        for (const label of labels) chips.append(make("span", "tag-chip", label));
        article.append(chips);
      }
      results.append(article);
    }
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runSearch();
  });
  input.addEventListener("input", runSearch);

  fetch(form.dataset.indexUrl)
    .then((response) => {
      if (!response.ok) throw new Error("Search index request failed");
      return response.json();
    })
    .then((data) => {
      pages = Array.isArray(data) ? data : [];
      indexedPages = pages.map((page) => ({
        page,
        title: normalize(page.title),
        url: normalize(page.url),
        slug: normalize(page.slug),
        virgoolId: normalize(page.virgool_id),
        originalUrl: normalize(page.original_url),
        summary: normalize(page.summary),
        content: normalize(page.content),
        tags: normalize((page.tags || []).join(" ")),
        categories: normalize((page.categories || []).join(" "))
      }));
      status.textContent = "جستجو در " + pages.length + " نوشته آماده است.";
      if (input.value.trim()) runSearch();
    })
    .catch(() => {
      status.textContent = "بارگذاری فهرست جستجو ناموفق بود. صفحه را تازه‌سازی کنید یا بعداً دوباره تلاش کنید.";
      input.disabled = true;
      form.querySelector("button").disabled = true;
    });
})();