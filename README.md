# UI Testcase Studio

Interactive **read-only** functional test-case workbench: open a live embedded browser, navigate and **log in manually**, harvest UI controls (buttons / inputs / selects, including iframes), organize them as a module tree, then generate query-only test cases and export to Excel / Markdown / CSV.

> 浠呯敤浜?*鎺堟潈娴嬭瘯鐜**鐨勬煡璇?灞曠ず绫诲姛鑳介獙璇併€傞粯璁ょ害鏉燂細涓嶈璁°€佷笉鎵ц澧炲垹鏀瑰啓鎿嶄綔銆?
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Screenshots

![live view](docs/images/live-view.png)

> Place UI screenshots under docs/images/.

## Features

- **Live browser view** 鈥?address bar, click, type (manual login, no cookie paste required)
- **Element discovery** 鈥?buttons, inputs, selects, links; recursive iframe walk
- **Module tree** 鈥?`Module 鈫?Title1 鈫?Title2 鈫?Title3 鈫?Point 鈫?XX test/verify`
- **Human review** 鈥?mark points, annotate issues, pass / fail / ignore
- **Case generation** 鈥?query-only cases (optional LLM / multimodal assist)
- **Export** 鈥?`.xlsx` / `.md` / `.csv`

## Requirements

- Windows / macOS / Linux
- Python 3.10+
- Microsoft Edge or Google Chrome (Playwright `channel=msedge` / `chrome`; no separate Chromium download required)

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configure (optional LLM)

```bash
cp config.example.yaml config.yaml
# edit ai.base_url / ai.model / ai.vision_model
# or: export QTS_API_KEY=sk-...
```

## Run

```bash
python run.py
# open http://127.0.0.1:8787
```

Typical flow in the UI:

1. Click **鍚姩娴忚鍣?*
2. Type the target URL in the address bar 鈫?**鍓嶅線**
3. Click the live view to focus login fields, type account/password in the top input bar, press **Enter**
4. **鑷姩鍙戠幇鍏冪礌** 鈫?**鑷姩寤哄姛鑳界偣鏍?* (or add nodes manually)
5. Mark functional points, annotate pass/fail
6. **鐢熸垚娴嬭瘯鐢ㄤ緥** 鈫?**瀵煎嚭Excel**

## Project layout

```
鈹溾攢鈹€ LICENSE                 # MIT
鈹溾攢鈹€ README.md
鈹溾攢鈹€ requirements.txt
鈹溾攢鈹€ config.example.yaml
鈹溾攢鈹€ run.py                  # entry: python run.py
鈹溾攢鈹€ app/
鈹?  鈹溾攢鈹€ main.py             # FastAPI
鈹?  鈹溾攢鈹€ browser/            # Playwright live view + element extract
鈹?  鈹溾攢鈹€ discovery/          # optional HTTP discovery
鈹?  鈹溾攢鈹€ ai/                 # optional LLM case generation
鈹?  鈹斺攢鈹€ export/             # xlsx / md / csv
鈹溾攢鈹€ static/                 # web UI
鈹斺攢鈹€ docs/compose/spec/      # design notes
```

## Security & ethics

- Use only on systems you are authorized to test.
- The tool does **not** execute create/update/delete operations by design.
- Do not commit `config.yaml` or session cookies/tokens; they are gitignored.

## License

[MIT](LICENSE)

## Chinese quick start / 涓枃閫熻

| 姝ラ | 鎿嶄綔 |
|------|------|
| 鍚姩 | `python run.py` 鍚庢墦寮€ `http://127.0.0.1:8787` |
| 鐧诲綍 | 鍦板潃鏍忚緭鍏ョ綉鍧€锛屽湪椤甸潰瑙嗗浘閲岀偣閫夎緭鍏ユ骞舵墜鍔ㄧ櫥褰曪紙鏃犻渶绮樿创 Cookie锛?|
| 鍙戠幇 | 銆岃嚜鍔ㄥ彂鐜板厓绱犮€嶆姄鎸夐挳/杈撳叆妗嗭紙鍚?iframe锛?|
| 鏍?| 銆岃嚜鍔ㄥ缓鍔熻兘鐐规爲銆嶆垨鎵嬪姩锛氭ā鍧?鈫?涓€/浜?涓夌骇鏍囬 鈫?鍔熻兘鐐?|
| 鍒ゅ畾 | 鏍囨敞闂鍚庣偣閫氳繃 / 涓嶉€氳繃 |
| 鐢ㄤ緥 | 鐢熸垚娴嬭瘯鐢ㄤ緥 鈫?瀵煎嚭 Excel锛屽懡鍚嶃€屾ā鍧?鏍囬-鍔熻兘鐐?XX鍔熻兘鐐规祴璇?楠岃瘉銆?|

