// Filter the full-text index by Solar Hijri or Gregorian year and month.
(() => {
  const form = document.getElementById("history-filter"); if (!form) return;
  const calendar = document.getElementById("history-calendar"), yearSelect = document.getElementById("history-year"), monthSelect = document.getElementById("history-month");
  const status = document.getElementById("history-status"), results = document.getElementById("history-results"), pagination = document.getElementById("history-pagination");
  const prevButton = document.getElementById("history-prev"), nextButton = document.getElementById("history-next"), pageLabel = document.getElementById("history-page-label");
  const pageSize = 30; let pages = [], currentPage = 0;
  const monthNames = {
    persian: ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"],
    gregorian: Array.from({length:12}, (_, i) => new Intl.DateTimeFormat("fa-IR-u-ca-gregory", {month:"long",timeZone:"UTC"}).format(new Date(Date.UTC(2020,i,15))))
  };
  const getDateParts = (iso, mode) => {
    const date = new Date(iso + "T12:00:00Z"); if (Number.isNaN(date.getTime())) return null;
    if (mode === "gregorian") return {year:String(date.getUTCFullYear()), month:String(date.getUTCMonth()+1)};
    const parts = new Intl.DateTimeFormat("en-US-u-ca-persian", {year:"numeric",month:"numeric",timeZone:"UTC"}).formatToParts(date);
    return {year:parts.find(p=>p.type==="year")?.value, month:String(Number(parts.find(p=>p.type==="month")?.value))};
  };
  const formatDate = (iso, mode) => new Intl.DateTimeFormat(mode === "persian" ? "fa-IR-u-ca-persian" : "fa-IR-u-ca-gregory", {year:"numeric",month:"long",day:"numeric",timeZone:"UTC"}).format(new Date(iso+"T12:00:00Z"));
  const make = (tag, cls, value) => { const node=document.createElement(tag); if(cls) node.className=cls; if(value!==undefined) node.textContent=value; return node; };
  const refreshYears = () => {
    const old=yearSelect.value, years=[...new Set(pages.map(p=>getDateParts(p.date,calendar.value)?.year).filter(Boolean))].sort((a,b)=>Number(b)-Number(a));
    yearSelect.replaceChildren(new Option("همهٔ سال‌ها","")); years.forEach(y=>yearSelect.add(new Option(y,y))); if(years.includes(old)) yearSelect.value=old;
    monthSelect.replaceChildren(new Option("همهٔ ماه‌ها","")); monthNames[calendar.value].forEach((m,i)=>monthSelect.add(new Option(m,String(i+1))));
  };
  const render = () => {
    const hasDateFilter = Boolean(yearSelect.value || monthSelect.value);
    results.classList.toggle("history-default-view", !hasDateFilter);
    // With no year/month selected, show only the 12 oldest posts, oldest first.
    const filtered = hasDateFilter
      ? pages.filter(p=>{const d=getDateParts(p.date,calendar.value); return d && (!yearSelect.value||d.year===yearSelect.value) && (!monthSelect.value||d.month===monthSelect.value);})
      : pages.slice(-12).reverse();
    const total=Math.max(1,Math.ceil(filtered.length/pageSize)); currentPage=Math.min(currentPage,total-1); results.replaceChildren();
    filtered.slice(currentPage*pageSize,(currentPage+1)*pageSize).forEach(p=>{const article=make("article","post-card"), heading=make("h2","post-title"), link=make("a","",p.title||"بدون عنوان"); link.href=p.url; heading.append(link); article.append(heading,make("div","post-meta",formatDate(p.date,calendar.value))); if(p.summary) article.append(make("p","post-summary",p.summary)); results.append(article);});
    status.textContent = hasDateFilter
      ? (filtered.length ? filtered.length.toLocaleString("fa-IR")+" نوشته پیدا شد." : "برای این بازه نوشته‌ای پیدا نشد.")
      : (filtered.length ? "۱۲ نوشتهٔ قدیمی‌تر وبلاگ، از قدیمی به جدید نمایش داده شده‌اند." : "هنوز نوشته‌ای برای نمایش وجود ندارد.");
    pagination.hidden = !hasDateFilter || filtered.length<=pageSize; prevButton.disabled=currentPage===0; nextButton.disabled=currentPage>=total-1; pageLabel.textContent="صفحهٔ "+(currentPage+1).toLocaleString("fa-IR")+" از "+total.toLocaleString("fa-IR");
  };
  form.addEventListener("submit",e=>{e.preventDefault();currentPage=0;render();}); calendar.addEventListener("change",()=>{refreshYears();currentPage=0;render();});
  yearSelect.addEventListener("change",()=>{currentPage=0;render();}); monthSelect.addEventListener("change",()=>{currentPage=0;render();});
  prevButton.addEventListener("click",()=>{currentPage--;render();}); nextButton.addEventListener("click",()=>{currentPage++;render();});
  fetch(form.dataset.indexUrl).then(r=>{if(!r.ok)throw Error("Archive index unavailable");return r.json();}).then(data=>{pages=(Array.isArray(data)?data:[]).sort((a,b)=>b.date.localeCompare(a.date));refreshYears();render();}).catch(()=>{status.textContent="بارگذاری آرشیو ناموفق بود. لطفاً صفحه را تازه‌سازی کنید.";});
})();
