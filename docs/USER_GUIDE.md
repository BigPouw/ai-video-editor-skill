# AI Video Editor｜完整使用教學

這份教學寫給第一次使用 Codex、Claude Code、Gemini CLI 或 Google Antigravity 剪輯影片的同學。不需要學 FFmpeg 指令。

## 先理解三個角色

1. **AI 編碼工具**：看懂你的中文剪輯要求、整理素材與產生剪輯計畫。
2. **video-editor Skill**：提供統一操作方式，指引 AI 安全使用工具。
3. **FFmpeg + Python**：真正執行影片與音訊處理；不依賴某家 AI 模型的 API。

一般剪輯在本機完成。只有你明確要求並授權 ElevenLabs 自動字幕時，才會把指定媒體送往 ElevenLabs。

## 步驟一：準備環境

- 先安裝 [Python](https://www.python.org/downloads/)（3.10+）與 [FFmpeg](https://ffmpeg.org/download.html)。
- 確認終端機找得到 `python`（或 Windows `py -3`、macOS/Linux `python3`）、`ffmpeg`、`ffprobe`。
- 確認所選 AI 工具具備本機工作資料夾的讀寫權限，且允許執行命令。純網頁聊天頁面不等同於可執行本 Skill 的編碼工具。
- 透過 README 的 `gh skill install` 指令，依 Codex、Claude Code、Gemini CLI 或 Antigravity 擇一安裝。若看不到新技能，使用該工具的技能重新整理功能或重新開啟工作階段。

**常見 Windows 問題**：執行 `ffmpeg -version` 若顯示找不到命令，代表 FFmpeg 尚未安裝或未加入 PATH。先處理這件事再開始剪輯。

## 步驟二：放入素材

在電腦上建立一個資料夾，例如：

```text
旅行影片/
├── input/
│   ├── Taipei-A.mp4
│   ├── Taipei-B.mp4
│   ├── BGM.mp3
│   ├── subtitles.srt        # 選用
│   └── myfont.ttf           # 選用
└── output/                  # AI 自動建立
```

影片名稱不必固定；MP4、MOV 等 FFmpeg 能讀取的影片均可嘗試。音訊可用 MP3、WAV 等格式。**請不要把私人影片放進 GitHub 倉庫**。

如果有多個音檔，最好在名稱中標示 `music`／`voice`，減少 AI 混淆。第一次先用 1–2 段短片測試。

## 步驟三：讓 AI 剪片

在 AI 編碼工具中開啟「旅行影片」工作資料夾，輸入：

> 使用 video-editor Skill。請把 input 的 Taipei-A.mp4 第 2～6 秒，接上 Taipei-B.mp4 第 1～7 秒，製作 9:16 Shorts。轉場交叉淡化 0.4 秒，保留原聲，加入 BGM.mp3（音量 20%）；開頭顯示「台北一日遊」2 秒，最後畫面與音樂淡出 0.5 秒。輸出 MP4。

AI 應先讀取媒體資訊（長度、有無音軌），然後製作 `edit-plan.json` 並執行附帶的 Python 腳本。若要求模糊，AI 會先提出必要的簡短問題。**不應根據檔名假裝已看懂影片劇情或知道哪個鏡頭最精彩。**

有多個片段但沒有指定時間時，預設使用完整素材，依檔名排序製作第一版。輸出若已存在，不會被覆寫。

也可以用更短的方式要求：

- 「把這支影片的前 15 秒改成直式 Shorts，補上片頭標題。」
- 「合併 input 裡兩段影片，中間使用 0.5 秒左右擦除轉場。」
- 「音樂太大聲，降到 10%；字幕改成白字黑邊。」
- 「第二段加速 1.25 倍，其他不變。」

## 步驟四：檢查成品

到 `output/` 開啟 `edited.mp4`（或依計畫設定的檔名）。請留意：

- 開頭與結尾是否正常、是否黑畫面。
- 是否切到重要人物；9:16 裁切可能截掉畫面兩側。若被裁切，告訴 AI「使用留黑邊的 pad，不要裁掉畫面」。
- 音量是否舒服；轉場時對話是否被背景音樂蓋住。
- 字幕有沒有錯字、重疊或超出畫面。

有問題直接請 AI 修改。範例：「字幕再大 20%，第二段改成硬切，背景音樂降低到 15%。」AI 應建立新版本，不覆寫原始影片。

## 字幕、文字與字型

### 已有 SRT

將字幕放在 `input/subtitles.srt`。它的時間碼應對齊**成品時間軸**，不是剪輯前原影片的絕對時間。可以用中文向 AI 指定：

> 使用 subtitles.srt，字幕白色、黑色描邊，字體 Noto Sans CJK TC，字體大小 54，位置在底部。

底層以 ASS 字幕渲染，預設字體為 Arial。中文字型通常可用系統已安裝的思源黑體、微軟正黑體等；不同作業系統的字型名稱可能不同。可以另附 TTF/OTF 並指定字型家族名稱，但必須讓字型檔內的實際家族名稱與設定一致。請以成片確認是否正確套用，避免缺字。

`title` 是片頭文字，不等同逐句字幕。可設定開始時間、結束時間與字體大小。

### 選用 ElevenLabs 自動字幕

若沒有 SRT、但影片有對話，ElevenLabs Scribe v2 可協助語音辨識並取得時間碼。這是**可選的第三方付費 API**，且需要把指定媒體上傳給 ElevenLabs。使用者未明確同意時，AI 不能呼叫。

流程：

1. 先照一般流程剪出沒有字幕的影片。
2. 確認你願意上傳該成品給 ElevenLabs、接受可能產生的費用，並自行在系統環境變數設定 `ELEVENLABS_API_KEY`。
3. 使用者明確授權後，AI 才執行下面的轉錄程序（以下為專案根目錄中的腳本路徑示例）：

```shell
python skills/video-editor/scripts/transcribe_elevenlabs.py "旅行影片/output/edited.mp4" --output "旅行影片/output/edited.srt" --confirm-api-cost
```

4. 人工檢查 SRT 是否正確，尤其人名、外語或雜音。
5. 將剪輯計畫的 `subtitles.file` 設定成 `output/edited.srt`，重新執行渲染，生成有字幕的下一版。

此最小版本接受小於 25 MiB 的輸入；較大的影片可先由 AI 使用 FFmpeg 擷取/壓縮音訊，再經你確認後上傳。**自動字幕不是完全免費，且目前只在有明確授權時執行。**

請勿把 API Key 寫入 `edit-plan.json`、`.env` 並提交到公開倉庫，或直接貼進公開討論區。

## 支援的剪輯設定

| 使用者常說的要求 | 剪輯計畫欄位 |
| --- | --- |
| 影片第 2 到 8 秒 | `clips[].start / end` |
| 第二段加速 1.5 倍 | `clips[].speed` |
| 直式/橫式/正方形 | `format: shorts / landscape / square` |
| 用黑邊保留完整畫面 | `fit: pad`（預設 `crop`） |
| 影片之間淡化 0.5 秒 | `transition: {type: fade, duration: 0.5}` |
| 淡入/淡出 | `fade.in / fade.out` |
| 原聲音量 100% | `original_audio_volume: 1.0` |
| 音樂音量 20% | `music.volume: 0.2` |
| 顯示標題 | `title.text / start / end` |
| 字幕字型與字號 | `subtitles.font / size / outline / color` |

輸出預設為 H.264/AAC MP4，Shorts 為 720×1280／30fps，橫式為 1280×720／30fps。可在計畫中使用 `resolution: [1080,1920]` 改為 1080p 直式，但轉檔會更久。

## 使用者常見問題

**Q：影片會被上傳到 GitHub 嗎？**

不會。一般剪輯在目前電腦/執行環境完成；GitHub 只放技能、腳本與公開文件。ElevenLabs 功能例外，必須明確授權，才會向第三方傳送檔案。

**Q：Claude Code / Gemini CLI 是否也能用？**

技能格式共用，前提是安裝成功、能執行本機 Python 和 FFmpeg，且對素材資料夾有權限。不同工具的沙箱與授權介面可能不同，需分別測試。

**Q：字幕顯示方框或字型不對？**

可能缺字型或系統上的字體家族名稱不同。先改用已安裝的中文字型，再重新輸出；必要時提供 TTF/OTF 並確認名稱。

**Q：為什麼兩段影片轉場會出錯？**

不同素材可能有不同解析度、FPS 或音軌。共用腳本會先將影片規格標準化；仍失敗時請保留錯誤訊息，讓 AI 調整為硬切或簡化轉場。

**Q：可以自動挑精彩片段嗎？**

第一版沒有提供內容理解／精華自動挑選。請指定時間、檔案順序或清楚的剪輯要求。

**Q：可以直接把影片發布到 YouTube 嗎？**

第一版不會自動發布，也沒有存取社群帳戶的功能；請自行確認版權、音樂授權與字幕後再上傳。
