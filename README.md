# AI Video Editor Skill

讓 Codex、Claude Code、Google Antigravity 等具備本機檔案與終端機操作能力的 AI 工具，透過自然語言剪輯影片。**Google AI Pro 使用者建議優先使用 Antigravity**。

> 狀態：v0.1 公開測試版。已完成 Windows + Codex 本機 MVP 驗證；其他 AI 工具／系統目前屬技術相容性分析，**未宣稱實機驗證通過**。

## 零基礎：下載後，先把專案交給 AI

1. 用 GitHub 的 **Code → Download ZIP** 下載並解壓縮（或使用 `git clone https://github.com/BigPouw/ai-video-editor-skill.git`）。
2. 用 [Google Antigravity](https://antigravity.google/)（推薦 Google AI Pro 使用者）、Codex 或 Claude Code 開啟解壓後的專案資料夾。
3. 在專案內建立 `input/`，放入要剪的 MP4／MOV、MP3／WAV；不要把私人素材提交到 GitHub。
4. **第一次先貼這段環境準備提示詞**：

```text
請先閱讀本專案的 README.md、docs/USER_GUIDE.md 與 skills/video-editor/SKILL.md。
我要使用 video-editor 剪輯本機影片；請幫我確認 Python 3.10+、ffmpeg、ffprobe 是否可用，
也檢查目前 AI 工具能否讀取本專案、執行終端機與使用這份 Skill。
若找不到 ffmpeg／ffprobe，先搜尋本機已有但未加入 PATH 的版本；仍缺少時，
優先從 FFmpeg 官方下載頁面列出的可信來源，下載可攜版至工作資料夾的 `.tools/`，
只對執行剪輯的命令設定 PATH，驗證後自動繼續。
若缺少 Python、需要管理員權限／系統設定變更、來源無法確認，
或 AI 平台要求授權，才停下來詢問；不要繞過平台權限限制。
若 Skill 無法直接安裝，先依 SKILL.md 使用本專案附帶的腳本即可。
完成後請確認 input/ 與 output/ 資料夾；不要刪除或覆蓋我的素材、
不要呼叫付費 API、不要把影片上傳到 GitHub，也不要發布影片。
準備好後告訴我可以開始下剪輯指令。
```

AI 可以協助檢查與準備環境。FFmpeg／ffprobe 優先使用既有版本或專案內的可攜版；安裝 Python、修改系統設定或平台權限確認仍可能需要使用者操作。純聊天網頁、沒有終端機權限的 AI 無法執行本機剪輯。

## 複製這段話，讓 AI 幫你剪

把素材放進工作資料夾的 `input/`，在 AI 工具開啟該資料夾，貼上這段話並換成你的檔名。

```text
請使用 video-editor Skill 剪輯 input/ 裡的素材。
先播［A.mp4］並搭配［X.mp3］，再播［B.mp4］並搭配［Y.mp3］。
兩段之間交叉淡化［0.5］秒，輸出［9:16］直式影片到 output/final.mp4。
其他設定用預設值，保留原始檔，全程在本機處理。
請先列出影片和配樂的對應，確認素材長度與音軌，再剪輯並驗證成品。
如果找不到素材或要求有衝突，請先問我。
```

AI 會建立剪輯計畫並執行，你只需要提供素材和剪輯指令。若要從頭到尾使用同一首歌，可以直接說「全片使用 BGM.mp3」。

## 可以做什麼？

- 將一段或多段影片裁切、排序、合併。
- 輸出 9:16 Shorts、16:9 或 1:1 MP4。
- 保留原聲，為每段影片各自配樂，或為全片使用一首背景音樂。可調整音量及淡入淡出。
- 選擇硬切、交叉淡化、左右擦除轉場；設定片段 0.5–2 倍播放速度。
- 加上片頭文字與既有 SRT 字幕，設定字型名稱、大小、顏色、描邊。
- **選用** ElevenLabs Scribe 自動生成 SRT；需要自己的 API Key，會將媒體上傳到第三方並可能產生費用，預設絕不呼叫。

這是「指令型剪輯」，不是能自動理解精彩橋段的影片分析模型。**不是所有剪輯技巧都能做**：完整的功能、可調參數與尚未支援的效果，見 [剪輯能力清單](docs/USER_GUIDE.md#完整剪輯能力清單)。

## 1. 必要環境（也可以請 AI 協助安裝）

需在**執行 AI 的電腦或容器**上備妥：

- Python 3.10 以上（不需要額外 pip 套件）。
- [FFmpeg](https://ffmpeg.org/download.html)，包含 `ffmpeg` 和 `ffprobe`。
- Codex、Claude Code、Antigravity 等任一可操作本機檔案／終端機的 AI 工具。

在終端機確認：

```shell
python --version
ffmpeg -version
ffprobe -version
```

Windows 若 `python` 不可用，可試 `py -3`；macOS/Linux 通常是 `python3`。

## 2. 安裝 Skill

如果已安裝支援 `gh skill` 的 [GitHub CLI](https://cli.github.com/)，可擇一執行；**新手不必先手動學會這些指令，交給 AI 協助即可**：

```shell
# Codex
gh skill install BigPouw/ai-video-editor-skill video-editor --agent codex --scope user

# Claude Code
gh skill install BigPouw/ai-video-editor-skill video-editor --agent claude-code --scope user

# Google Antigravity（Google AI Pro 推薦）
gh skill install BigPouw/ai-video-editor-skill video-editor --agent antigravity --scope user
```

如果倉庫尚未公開，需先取得 GitHub 存取權限；公開後才可匿名下載。這些指令需要具有 `gh skill` 功能的 GitHub CLI。若命令不可用，AI 仍可**直接閱讀** [SKILL.md](skills/video-editor/SKILL.md) 並執行倉庫內的腳本；Antigravity 亦支援將技能資料夾放到 `.agents/skills/video-editor/`。不同工具的技能重新載入機制可能不同，尚未逐一實測。

## 3. 準備素材

可直接在下載的 Repo 裡建立 `input/`，也能另建獨立工作資料夾；**影片不用上傳到 GitHub**：

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

詳細字型、字幕、操作和排錯方式見 [使用者教學](docs/USER_GUIDE.md)。

## 4. 手動執行（不用 AI）

從 GitHub 下載/複製此專案後，可參考 [範例計畫](examples/edit-plan.json) 自行建立工作資料夾中的 `edit-plan.json`：

```shell
python skills/video-editor/scripts/render.py /path/to/你的影片專案/edit-plan.json --dry-run
python skills/video-editor/scripts/render.py /path/to/你的影片專案/edit-plan.json
```

請把 `/path/to/...` 換成真實路徑；Windows 可使用完整路徑。範例裡的素材檔名只是示意，必須有實際媒體才能渲染。

## ElevenLabs 自動字幕（自願、付費）

有 `captions.srt` 就完全不需要 API。已保留 **ElevenLabs 選用介面／腳本**，但**沒有使用付費帳號實際呼叫驗證**。若希望 AI 從影片產生字幕，必須另行明確同意上傳媒體和可能的費用，並設定自己的 `ELEVENLABS_API_KEY`。詳見 [使用者教學](docs/USER_GUIDE.md#選用-elevenlabs-自動字幕)。

**不要把 API Key 放進對話、GitHub 或範例檔案。**

## 安全與限制

- 媒體檔、API 金鑰和輸出不應提交到 GitHub；本倉庫已提供 `.gitignore`。
- 腳本只讀取指定專案資料夾內的檔案，輸出只寫入 `output/`，同名成品自動使用 `_v2` 等新檔名。
- 使用者必須有影音素材授權；公開作品前請檢查字幕、音樂和最終畫面。
- 本工具不保證自動挑精彩片段、卡點、物件追蹤或複雜動態排版。
- Windows／macOS／Linux 與各種 AI 工具的實機相容性尚未逐一驗證；可行性分析見 [工具相容性](docs/USER_GUIDE.md#不同-ai-工具可行性)。
- 本機 FFmpeg 剪輯不等於 AI 服務完全離線；若 AI 主動讀取、分析媒體，仍須留意該 AI 工具的檔案傳送與隱私規範。

## 開發測試

```shell
python -m unittest discover -s tests -v
```

測試會在暫存資料夾產生合成素材，不需要下載影片、不呼叫付費 API。

授權：[MIT](LICENSE)。
