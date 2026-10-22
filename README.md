# Ryan's Muse Feed — RSS

An RSS 2.0 feed built from Ryan's personal Muse Feed: the daily digests
(morning, midday, evening), the Daily Learning trio (Word of the Day, Big
Idea, Statistics), the Weekly Music Update, and other Feed posts.

**Subscribe URL:**

https://raw.githubusercontent.com/rynglvr/feed-rss/main/feed.xml

Paste that URL into any RSS reader (NetNewsWire, Feedly, Reeder, etc.).

## How it works

- `units.json` holds the most recent ~50 Muse Feed posts (newest first),
  pulled from the Feed.
- `build_feed.py` (Python, stdlib only) converts `units.json` into
  `feed.xml`: each post becomes an RSS item with its title, publication
  date, category, a short plain-text description, and the full body as
  HTML in `content:encoded`.
- `feed.xml` is regenerated and pushed to this repo on a schedule, so
  the feed auto-updates from the Muse Feed — new posts appear here
  without any manual step.

Run it locally:

```sh
python3 build_feed.py units.json --out feed.xml
```
