# AnhängerDirekt — separate German TIKI dealer catalogue

A deployable static site with a scheduled catalogue sync. Does not modify tiki-anhaenger.de. It is deliberately **not** a cloned TIKI site and does not assert that a trailer is in stock in Germany.

## One-time live deployment (without writing code)

1. Create a new **private or public GitHub repository** and upload the *contents* of this project (including `.github` folder), ideally using GitHub desktop or repository web upload. Note: GitHub's web upload may not preserve hidden directories reliably; check that `.github/workflows/sync.yml` exists.
2. In repository **Settings → Secrets and variables → Actions → New repository secret**, create `OPENAI_API_KEY` (required for faithful automatic German product descriptions). Without it, titles are translated by a dictionary and descriptions are intentionally omitted instead of displaying Estonian as German.
3. In **GitHub → Actions → TIKI catalogue sync → Run workflow**, run the importer. It discovers TIKI product links via sitemap + all 11 product categories, extracts the explicitly marked `ilma KM-ta` net prices, images, gallery drawings, PDFs, identifiers and specifications, adds €1000 and 19% German VAT, and writes `data/catalog.json`. Check the action log and resulting product count (if site markup changes, fix selectors; source is not guaranteed stable).
4. In **Netlify → Add new project → Import an existing project → GitHub**, select that repo. Build command: leave blank. Publish directory: `.`. Netlify will deploy automatically on each GitHub commit. GitHub schedule checks daily at 03:20 UTC and publishes changes.
5. Attach a *new* domain using Netlify Domain management and point its DNS records according to the instructions Netlify shows. Your previous and current TIKI domain remains unchanged.
6. Complete mandatory legal pages (representative's name, register court, contact details, reviewed GDPR notice). Turn on Netlify Forms detection and set email notifications so customer inquiries reach your mailbox. **Do not accept customer enquiries commercially before legal notices are reviewed.**

## Pricing

Price shown in Germany = `(explicit TIKI Estonia net price + €1000) × 1.19` rounded to cents. Delivery price is not included. A €1000 selling spread is not net profit. Sale, availability, shipping and VAT treatment must be checked for specific transactions.

## Technical note

The importer runs inside GitHub Actions with internet access, **not inside the static Netlify page**. Netlify serves the generated `data/catalog.json`. This is simpler and more reliable than scraping TIKI on every website visit. A failed import never intentionally overwrites the last good catalogue. Source gallery image URLs are linked to the TIKI origin; images are not locally downloaded. If image hotlinking is blocked, use approved image storage/CDN and update importer.

## Optional Make.com

Once a Make scenario exists, it can consume `https://YOUR-DOMAIN/data/catalog.json` via HTTP GET and handle price changes, inquiries, CRM, or cross-posting to third party marketplace APIs. No third-party marketplace API access is included here; external platforms require their own credentials/approval. **Make cannot replace the hosting/domain registration process.**

## Known limitations

- This environment cannot make direct external HTTP requests and has not executed a full live TIKI crawl. Parsing needs one live GitHub Actions test.
- Website seed catalogue is empty on purpose; no fabricated images or prices.
- The source may contain trailers plus accessories in product sitemap, so catalogue completeness/category classification must be validated after first sync.
- Descriptions are translated only when OPENAI_API_KEY is configured.
- To prevent double selling, every product is enquiry-only; no checkout, no automated stock guarantee.
- This is a full deployment project, **not an already live fully synchronized store**.
