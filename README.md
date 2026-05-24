# TikTok User Lookup UI

A web interface to search TikTok profiles by username and view detailed user information. Built on top of [TikTok-User-Info-Scraper](https://github.com/N4rr34n6/TikTok-User-Info-Scraper).

## Setup

```bash
cd /Users/cookie/tiktok
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## Usage

1. Enter a TikTok username (with or without `@`)
2. Click **Search**
3. View profile stats, bio, avatar, and social links

## Notes

- Only **public** TikTok accounts can be looked up
- Scraping depends on TikTok's page structure and may break if they change it
- The original CLI scraper is available in the `scraper/` directory

## License

The underlying scraper is licensed under AGPL-3.0. See [scraper/LICENSE](scraper/LICENSE).
