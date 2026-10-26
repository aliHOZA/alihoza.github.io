# گزارش نهایی بهینه‌سازی تصاویر بزرگ

- روش: تبدیل lossy به WebP با کیفیت ۹۰ و method=6
- آستانه: بیش از ۷۰۰ KiB (۷۱۶٬۸۰۰ بایت)
- تصاویر thumbnail و تصاویر متحرک از تبدیل مستثنا هستند.
- فایل‌های بزرگ بررسی‌شده در اجرای اولیه: ۶
- تعداد تصاویر جایگزین‌شده: ۵
- تعداد تصاویر حفظ‌شده به‌دلیل صرفه‌جویی ناکافی: ۱
- شرط جایگزینی: WebP دست‌کم ۱۰٪ کوچک‌تر از فایل اصلی باشد.
- حجم پنج تصویر جایگزین‌شده پیش از تبدیل: ۳٬۷۰۴٬۴۹۰ بایت (۳٫۵۳ MiB)
- حجم WebPهای جایگزین‌شده: ۳۳۸٬۱۹۶ بایت (۰٫۳۲ MiB)
- صرفه‌جویی خالص: ۳٬۳۶۶٬۲۹۴ بایت (۳٫۲۱ MiB، معادل ۹۰٫۹٪)

| فایل اصلی | حجم اولیه (KiB) | فایل WebP | حجم WebP (KiB) | صرفه‌جویی (KiB) |
|---|---:|---|---:|---:|
| `static/images/virgool/413a14c72aa38ce4459c.png` | 725.0 | `static/images/virgool/413a14c72aa38ce4459c.webp` | 57.7 | 667.4 |
| `static/images/virgool/4f35ebe7ab018c93441f.png` | 734.1 | `static/images/virgool/4f35ebe7ab018c93441f.webp` | 71.6 | 662.5 |
| `static/images/virgool/5516ee5c1472a9a0a3b2.png` | 717.4 | `static/images/virgool/5516ee5c1472a9a0a3b2.webp` | 83.8 | 633.7 |
| `static/images/virgool/7d0addb628e67070cf65.png` | 725.9 | `static/images/virgool/7d0addb628e67070cf65.webp` | 74.0 | 651.9 |
| `static/images/virgool/e0192274766cd6cc32c6.png` | 715.2 | `static/images/virgool/e0192274766cd6cc32c6.webp` | 43.2 | 672.0 |

## فایل حفظ‌شده

`static/images/virgool/a598c3090b51de98b750.jpeg` — حجم اصلی ۷۱۵٫۱ KiB؛ خروجی آزمایشی WebP برابر ۸۵۹٫۵ KiB بود، بنابراین فایل اصلی و ارجاع آن در مطلب حفظ شد.
