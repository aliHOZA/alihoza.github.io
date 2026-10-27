(() => {
  const list = document.querySelector(".random-post-list");
  const script = document.currentScript;
  const indexUrl = script?.dataset.indexUrl;
  if (!list || !indexUrl) return;

  const dateFormatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    year: "numeric", month: "long", day: "numeric", timeZone: "UTC"
  });

  const shuffle = (items) => {
    const result = [...items];
    for (let i = result.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  };

  const makeCard = (post) => {
    const article = document.createElement("article");
    article.className = "post-card";

    if (post.thumbnail && post.slug) {
      const thumbnailLink = document.createElement("a");
      thumbnailLink.className = "post-thumbnail";
      thumbnailLink.href = post.url;
      thumbnailLink.setAttribute("aria-hidden", "true");
      thumbnailLink.tabIndex = -1;

      const image = document.createElement("img");
      image.src = "/images/thumbnails/" + encodeURIComponent(post.slug) + ".webp";
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
    const link = document.createElement("a");
    link.href = post.url;
    link.textContent = post.title || "بدون عنوان";
    heading.append(link);
    main.append(heading);

    const meta = document.createElement("div");
    meta.className = "post-meta";
    if (post.date) {
      const time = document.createElement("time");
      time.dateTime = post.date;
      const date = new Date(post.date + "T12:00:00Z");
      if (!Number.isNaN(date.getTime())) time.textContent = dateFormatter.format(date);
      meta.append(time);
    }
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
    return article;
  };

  fetch(indexUrl)
    .then((response) => {
      if (!response.ok) throw new Error("Random post index request failed");
      return response.json();
    })
    .then((posts) => {
      if (!Array.isArray(posts)) throw new Error("Invalid random post index");
      // Keep the eight newest posts out of the recommendations, as before.
      const candidates = posts.slice(8).filter((post) => post && post.url && post.title);
      if (!candidates.length) return;
      const selected = shuffle(candidates).slice(0, 4);
      if (!selected.length) return;
      list.replaceChildren(...selected.map(makeCard));
    })
    .catch(() => {
      // Keep Hugo's original static recommendations if the index cannot be loaded.
    });
})();
