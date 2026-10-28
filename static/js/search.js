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
  let debounceTimer = 0;

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

  // Normalize and split fields once when the index loads, not on every keystroke.
  const tokenize = (value) => normalize(value).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  const hasPrefix = (words, term) => words.some((word) => word.startsWith(term));

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const renderResults = (found) => {
    const shown = found.slice(0, 50);
    status.textContent = found.length
      ? (found.length + " نتیجه پیدا شد" + (found.length > shown.length ? "؛ ۵۰ نتیجهٔ نخست نمایش داده شده‌اند." : ""))
      : "نتیجه‌ای پیدا نشد. عبارت دیگری را امتحان کنید.";

    const fragment = document.createDocumentFragment();
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
      article.append(make("div", "post-meta", displayDate));

      if (page.summary) article.append(make("p", "post-summary", page.summary));

      const labels = [...(page.tags || []), ...(page.categories || [])].slice(0, 5);
      if (labels.length) {
        const chips = make("div", "tag-row");
        for (const label of labels) chips.append(make("span", "tag-chip", label));
        article.append(chips);
      }
      fragment.append(article);
    }
    results.replaceChildren(fragment);
  };

  const runSearch = () => {
    const query = normalize(input.value);
    results.replaceChildren();

    if (query.length < 2) {
      status.textContent = "برای جستجو دست‌کم دو نویسه وارد کنید.";
      return;
    }

    // Numeric post-number searches can bypass the full-text scan entirely.
    if (/^\d+$/.test(query)) {
      const requestedNumber = Number(query);
      const numberedPost = indexedPages.find((item) => item.postNumber === requestedNumber);
      if (numberedPost) {
        renderResults([{ page: numberedPost.page, score: 1000, item: numberedPost }]);
        return;
      }
    }

    const terms = query.split(" ").filter(Boolean);
    const found = [];
    for (const item of indexedPages) {
      let score = 0;
      let matchesAllTerms = true;

      for (const term of terms) {
        const titleMatch = hasPrefix(item.titleWords, term);
        const urlMatch = item.url.includes(term) || item.slug.includes(term) ||
          item.virgoolId.includes(term) || item.originalUrl.includes(term);
        const tagsMatch = hasPrefix(item.tagWords, term);
        const categoriesMatch = hasPrefix(item.categoryWords, term);
        const summaryMatch = hasPrefix(item.summaryWords, term);
        const contentMatch = hasPrefix(item.contentWords, term);

        if (!(titleMatch || urlMatch || tagsMatch || categoriesMatch || summaryMatch || contentMatch)) {
          matchesAllTerms = false;
          break;
        }

        if (titleMatch) score += 12;
        if (urlMatch) score += 10;
        if (tagsMatch) score += 7;
        if (categoriesMatch) score += 6;
        if (summaryMatch) score += 4;
        if (contentMatch) score += 1;
      }

      if (matchesAllTerms && score > 0) found.push({ page: item.page, score });
    }

    found.sort((a, b) => b.score - a.score || b.page.date.localeCompare(a.page.date));
    renderResults(found);
  };

  const scheduleSearch = () => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(runSearch, 90);
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    window.clearTimeout(debounceTimer);
    runSearch();
  });
  input.addEventListener("input", scheduleSearch);

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
        titleWords: tokenize(page.title),
        url: normalize(page.url),
        slug: normalize(page.slug),
        virgoolId: normalize(page.virgool_id),
        originalUrl: normalize(page.original_url),
        summaryWords: tokenize(page.summary),
        contentWords: tokenize(page.content),
        tagWords: tokenize((page.tags || []).join(" ")),
        categoryWords: tokenize((page.categories || []).join(" "))
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
