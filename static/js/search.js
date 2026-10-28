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
    // Treat Persian and Arabic-Indic numerals the same as ASCII digits.
    .replace(/[۰-۹٠-٩]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩".indexOf(digit) % 10))
    .replace(/ك/g, "ک")
    // Normalize Persian half-space as a word boundary, so either spacing form matches.
    .replace(/[\u200c\u200d]/g, " ")
    .replace(/[\u064B-\u065F\u0670\u0640]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  // Match whole words or their prefixes in natural-language fields.
  // This avoids matching "سلام" inside "اسلام", while "اسلا" matches "اسلام".
  const wordStartsWith = (field, term) => normalize(field)
    .split(/[^\p{L}\p{N}]+/u)
    .some((word) => word.startsWith(term));

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
    let found = indexedPages.map((item) => {
      let score = 0;
      for (const term of terms) {
        if (wordStartsWith(item.title, term)) score += 12;
        // URL/slug/legacy IDs deliberately support substring matching.
        if ([item.url, item.slug, item.virgoolId, item.originalUrl].some((field) => field.includes(term))) score += 10;
        if (wordStartsWith(item.tags, term)) score += 7;
        if (wordStartsWith(item.categories, term)) score += 6;
        if (wordStartsWith(item.summary, term)) score += 4;
        if (wordStartsWith(item.content, term)) score += 1;
      }
      const matchesTerm = (term) =>
        wordStartsWith(item.title, term) ||
        [item.url, item.slug, item.virgoolId, item.originalUrl].some((field) => field.includes(term)) ||
        [item.summary, item.content, item.tags, item.categories].some((field) => wordStartsWith(field, term));

      return { page: item.page, score, item, matchesAllTerms: terms.every(matchesTerm) };
    }).filter(({ score, matchesAllTerms }) => score > 0 && matchesAllTerms)
      .sort((a, b) => b.score - a.score || b.page.date.localeCompare(a.page.date));

    // Number posts by publication order, oldest first; exact numeric searches take precedence.
    if (/^\\d+$/.test(query)) {
      const requestedNumber = Number(query);
      const numberedPost = indexedPages.find((item) => item.postNumber === requestedNumber);
      if (numberedPost) found = [{ page: numberedPost.page, score: 1000, item: numberedPost, matchesAllTerms: true }];
    }

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
      const chronologicalPages = [...pages].sort((a, b) =>
        String(a.date || "").localeCompare(String(b.date || "")) ||
        String(a.slug || "").localeCompare(String(b.slug || "")));
      const postNumbers = new Map(chronologicalPages.map((page, index) => [page.url, index + 1]));
      indexedPages = pages.map((page) => ({
        page,
        postNumber: postNumbers.get(page.url),
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