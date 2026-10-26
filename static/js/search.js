(() => {
  const form = document.getElementById("site-search");
  if (!form) return;

  const input = document.getElementById("search-query");
  const status = document.getElementById("search-status");
  const results = document.getElementById("search-results");
  let pages = [];

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
    const found = pages.map((page) => {
      const title = normalize(page.title);
      const summary = normalize(page.summary);
      const content = normalize(page.content);
      const tags = normalize((page.tags || []).join(" "));
      const categories = normalize((page.categories || []).join(" "));
      let score = 0;

      for (const term of terms) {
        if (title.includes(term)) score += 12;
        if (tags.includes(term)) score += 7;
        if (categories.includes(term)) score += 6;
        if (summary.includes(term)) score += 4;
        if (content.includes(term)) score += 1;
      }
      return { page, score };
    }).filter((item) => item.score > 0 && terms.every((term) => {
      const p = item.page;
      return [p.title, p.summary, p.content, (p.tags || []).join(" "), (p.categories || []).join(" ")]
        .some((field) => normalize(field).includes(term));
    })).sort((a, b) => b.score - a.score || b.page.date.localeCompare(a.page.date));

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

      const meta = make("div", "post-meta", page.date || "");
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
      status.textContent = "جستجو در " + pages.length + " نوشته آماده است.";
      if (input.value.trim()) runSearch();
    })
    .catch(() => {
      status.textContent = "بارگذاری فهرست جستجو ناموفق بود. صفحه را تازه‌سازی کنید یا بعداً دوباره تلاش کنید.";
      input.disabled = true;
      form.querySelector("button").disabled = true;
    });
})();
