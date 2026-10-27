(() => {
  const link = document.getElementById("random-post-link");
  const indexUrl = link?.dataset.indexUrl;
  if (!indexUrl) return;

  const chooseRandomPost = async () => {
    link?.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(indexUrl);
      if (!response.ok) throw new Error("Could not load post index");
      const posts = await response.json();
      if (!Array.isArray(posts) || posts.length === 0) throw new Error("No posts found");

      const currentPath = window.location.pathname.replace(/\/$/, "");
      let candidates = posts.filter((post) => {
        try {
          return new URL(post.url, window.location.origin).pathname.replace(/\/$/, "") !== currentPath;
        } catch {
          return true;
        }
      });
      if (candidates.length === 0) candidates = posts;

      const post = candidates[Math.floor(Math.random() * candidates.length)];
      window.location.href = post.url;
    } catch (error) {
      // Keep the landing page usable if the post index is unavailable.
      const isRandomPage = window.location.pathname.replace(/\/$/, "").endsWith("/random");
      if (isRandomPage) {
        const message = document.querySelector("main p");
        if (message) message.textContent = "انتخاب خودکار ممکن نشد. لطفاً دوباره تلاش کنید یا به صفحهٔ اصلی وبلاگ برگردید.";
        link?.removeAttribute("aria-busy");
      } else {
        window.location.href = link.href;
      }
    } finally {
      link?.removeAttribute("aria-busy");
    }
  };


  const recommendationList = document.getElementById("random-post-list");
  if (recommendationList) {
    const recommendationsUrl = recommendationList.dataset.indexUrl || indexUrl;
    const latestList = document.querySelector('.post-list[aria-label="آخرین نوشته‌ها"]');
    const latestUrls = new Set(Array.from(latestList?.querySelectorAll(".post-title a") || []).map((a) => {
      try { return new URL(a.href, window.location.origin).pathname.replace(/\/$/, ""); }
      catch { return ""; }
    }));

    const shuffle = (items) => {
      const result = [...items];
      for (let i = result.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
      }
      return result;
    };

    const renderRecommendations = (posts) => {
      if (!Array.isArray(posts)) return;
      const candidates = posts.filter((post) => {
        try {
          const path = new URL(post.url, window.location.origin).pathname.replace(/\/$/, "");
          return !latestUrls.has(path);
        } catch { return false; }
      });
      const selected = shuffle(candidates).slice(0, 4);
      if (selected.length === 0) return;

      const formatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
        year: "numeric", month: "long", day: "numeric", timeZone: "UTC"
      });
      const fragment = document.createDocumentFragment();

      for (const post of selected) {
        const article = document.createElement("article");
        article.className = "post-card";

        if (post.thumbnailUrl) {
          const thumbnailLink = document.createElement("a");
          thumbnailLink.className = "post-thumbnail";
          thumbnailLink.href = post.url;
          thumbnailLink.setAttribute("aria-hidden", "true");
          thumbnailLink.tabIndex = -1;
          const image = document.createElement("img");
          image.src = post.thumbnailUrl;
          image.alt = "";
          image.loading = "lazy";
          image.decoding = "async";
          image.width = 120;
          image.height = 90;
          thumbnailLink.append(image);
          article.append(thumbnailLink);
        }

        const main = document.createElement("div");
        main.className = "post-card-main";
        const heading = document.createElement("h3");
        heading.className = "post-title";
        const titleLink = document.createElement("a");
        titleLink.href = post.url;
        titleLink.textContent = post.title || "بدون عنوان";
        heading.append(titleLink);
        main.append(heading);

        const meta = document.createElement("div");
        meta.className = "post-meta";
        const time = document.createElement("time");
        time.className = "js-local-date";
        time.dataset.date = post.date || "";
        time.dateTime = post.date || "";
        const date = new Date(String(post.date || "") + "T12:00:00Z");
        if (!Number.isNaN(date.getTime())) time.textContent = formatter.format(date);
        meta.append(time);
        if (post.readingTime) {
          const reading = document.createElement("span");
          reading.textContent = post.readingTime + " دقیقه مطالعه";
          meta.append(reading);
        }
        main.append(meta);

        if (post.summary) {
          const summary = document.createElement("p");
          summary.className = "post-summary";
          summary.textContent = post.summary;
          main.append(summary);
        }
        article.append(main);

        const number = document.createElement("span");
        number.className = "post-number";
        number.setAttribute("aria-hidden", "true");
        number.textContent = String(post.number || "").padStart(2, "0");
        article.append(number);
        fragment.append(article);
      }
      recommendationList.replaceChildren(fragment);
    };

    fetch(recommendationsUrl)
      .then((response) => {
        if (!response.ok) throw new Error("Recommendation index request failed");
        return response.json();
      })
      .then(renderRecommendations)
      .catch(() => {
        // Keep Hugo's original server-rendered recommendations if the index is unavailable.
      });
  }


  link.addEventListener("click", (event) => {
    event.preventDefault();
    chooseRandomPost();
  });

  // The static /random/ page also works as a direct entry point or fallback.
  if (window.location.pathname.replace(/\/$/, "").endsWith("/random")) {
    chooseRandomPost();
  }
})();