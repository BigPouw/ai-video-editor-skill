# AI Video Editor Skill

讓 Codex、Claude Code、Gemini CLI、Google Antigravity 使用同一套技能，透過自然語言剪輯本機影片。

> 狀態：v0.1 開發預覽版。**請先在本機測試，尚未完成四種 AI 工具的實機驗證。**

## 可以做什麼？

- 將一段或多段影片裁切、排序、合併。
- 輸出 9:16 Shorts、16:9 或 1:1 MP4。
- 保留原聲、混入背景音樂、調整音量及淡入淡出。
- 選擇硬切、交叉淡化、左右擦除轉場；設定片段 0.5–2 倍播放速度。
- 加上片頭文字與既有 SRT 字幕，設定字型名稱、大小、顏色、描邊。
- **選用** ElevenLabs Scribe 自動生成 SRT；需要自己的 API Key，會將媒體上傳到第三方並可能產生費用，預設絕不呼叫。

這是「指令型剪輯」，不是能自動理解精彩橋段的影片分析模型。

## 1. 安裝必要工具

需在**執行 AI 的電腦或容器**上備妥：

- Python 3.10 以上（不需要額外 pip 套件）。
- [FFmpeg](https://ffmpeg.org/download.html)，包含 `ffmpeg` 和 `ffprobe`。
- Codex、Claude Code、Gemini CLI 或 Antigravity 任一可操作本機檔案/命令的工具。

在終端機確認：

```shell
python --version
ffmpeg -version
ffprobe -version
```

Windows 若 `python` 不可用，可試 `py -3`；macOS/Linux 通常是 `python3`。

## 2. 安裝 Skill

若已安裝支援 `gh skill` 的 [GitHub CLI](https://cli.github.com/)，擇一執行：

```shell
# Codex
gh skill install BigPouw/ai-video-editor-skill video-editor --agent codex --scope user

# Claude Code
gh skill install BigPouw/ai-video-editor-skill video-editor --agent claude-code --scope user

# Gemini CLI
gh skill install BigPouw/ai-video-editor-skill video-editor --agent gemini-cli --scope user

# Google Antigravity
gh skill install BigPouw/ai-video-editor-skill video-editor --agent antigravity --scope user
```

目前倉庫是 Private，只有有權限的 GitHub 使用者可以安裝；公開後同學才能直接使用。這些命令需要新版 GitHub CLI 的 `gh skill` 功能。也可以把 [Skill 資料夾](skills/video-editor/) 手動複製到對應工具的 Skills 目錄。

## 3. 準備素材

建立自己的工作資料夾；**影片不用上傳到 GitHub**：

```text
我的影片專案/
├── input/
│   ├── 01.mp4
│   ├── 02.mov
│   ├── music.mp3
│   └── captions.srt   (選用)
└── output/            (AI 會建立)
```

在 AI 編碼工具中開啟「我的影片專案」，用自然語言說：

> 使用 video-editor，把 input 的 01.mp4 前 5 秒和 02.mov 的第 3～9 秒接起來，輸出 9:16 的 Shorts，片頭寫「我的大學生活」，中間交叉淡化 0.4 秒，加入 music.mp3、音量 20%，最後淡出 1 秒。

AI 會產生 `edit-plan.json` 並執行剪輯，成品在 `output/`。要求「字幕大一點」或「音樂再小聲」就能修改下一版；舊成品不會覆蓋。

詳細圖片/字型/字幕、操作和排錯方式見 [使用者教學](docs/USER_GUIDE.md)。

## 4. 手動執行（不用 AI）

從 GitHub 下載/複製此專案後，可參考 [範例計畫](examples/edit-plan.json) 自行建立工作資料夾中的 `edit-plan.json`：

```shell
python skills/video-editor/scripts/render.py /path/to/你的影片專案/edit-plan.json --dry-run
python skills/video-editor/scripts/render.py /path/to/你的影片專案/edit-plan.json
```

請把 `/path/to/...` 換成真實路徑；Windows 可使用完整路徑。範例裡的素材檔名只是示意，必須有實際媒體才能渲染。

## ElevenLabs 自動字幕（自願、付費）

有 `captions.srt` 就完全不需要 API。若希望 AI 從已剪好的影片產生字幕，需先明確同意把影片傳送到 ElevenLabs 並承擔相關用量，再設定 `ELEVENLABS_API_KEY`，由 AI 執行選用腳本。詳見 [使用者教學](docs/USER_GUIDE.md#選用-elevenlabs-自動字幕)。

**不要把 API Key 放進對話、GitHub 或範例檔案。**

## 安全與限制

- 媒體檔、API 金鑰和輸出不應提交到 GitHub；本倉庫已提供 `.gitignore`。
- 腳本只讀取指定專案資料夾內的檔案，輸出只寫入 `output/`，同名成品自動使用 `_v2` 等新檔名。
- 使用者必須有影音素材授權；公開作品前請檢查字幕、音樂和最終畫面。
- 本工具不保證自動挑精彩片段、卡點、物件追蹤或複雜動態排版。
- 完整的 Windows／macOS／Linux，以及各種 AI 工具實機相容性，仍需逐步驗證。

## 開發測試

```shell
python -m unittest discover -s tests -v
```

測試會在暫存資料夾產生合成素材，不需要下載影片、不呼叫付費 API。

授權：[MIT](LICENSE)。
