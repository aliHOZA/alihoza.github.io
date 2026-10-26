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

  link.addEventListener("click", (event) => {
    event.preventDefault();
    chooseRandomPost();
  });

  // The static /random/ page also works as a direct entry point or fallback.
  if (window.location.pathname.replace(/\/$/, "").endsWith("/random")) {
    chooseRandomPost();
  }
})();