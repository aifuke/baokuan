# 🔥 爆款视频反推分析工具 (Viral Video Analyzer)

一键拆解爆款视频的成功密码。输入视频 URL 或本地文件，自动生成结构化反推报告。

## 功能特性

- **多平台支持**: 抖音、快手、B站、YouTube、小红书等（基于 yt-dlp）
- **语音转文字**: OpenAI Whisper 多语言识别，输出带时间戳字幕
- **视觉分析**: 关键帧提取、场景切换检测、画面风格分析
- **文案拆解**: 开头钩子、内容节奏、转折点、情绪曲线、结尾CTA
- **爆款评分**: 五维度加权评分卡（互动数据/钩子/结构/视觉/发布策略）
- **标签分析**: 话题标签、关键词提取、标签策略评估
- **LLM 增强**: 可选接入 GPT 进行叙事结构、受众画像、可复用模板分析
- **Markdown 报告**: 生成完整的结构化反推分析报告

## 快速开始

```bash
# 分析在线视频
python main.py "https://www.bilibili.com/video/BV1xx411c7mD"

# 分析本地视频
python main.py ./my_video.mp4 --whisper-model small

# 启用 AI 深度分析
python main.py "https://www.douyin.com/video/xxx" --llm-enhance

# 指定输出目录和语言
python main.py "https://www.youtube.com/watch?v=xxx" -o ./report --language en
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `source` | 视频 URL 或本地路径 | (必填) |
| `-o, --output` | 输出目录 | `./output` |
| `--whisper-model` | Whisper 模型 (tiny/base/small/medium/large) | `base` |
| `--language` | 语言代码 (zh/en/ja...) | 自动检测 |
| `--max-resolution` | 最大下载分辨率 | `720` |
| `--cookies` | cookies 文件路径 | 无 |
| `--llm-enhance` | 启用 LLM 深度分析 | 关闭 |
| `--openai-api-key` | OpenAI API Key | 环境变量 |
| `--openai-base-url` | API Base URL | 官方 |
| `--openai-model` | LLM 模型 | `gpt-4o-mini` |

## 模块架构

```
viral_video_analyzer/
├── main.py                    # CLI 入口 & 流程编排
├── modules/
│   ├── video_downloader.py    # 视频下载 + 元数据提取
│   ├── audio_transcriber.py   # Whisper 语音转文字
│   ├── visual_analyzer.py     # 关键帧 + 场景检测 + 画面分析
│   ├── script_analyzer.py     # 文案结构拆解 + LLM 增强
│   ├── trend_analyzer.py      # 爆款元素分析 + 评分卡
│   └── report_generator.py    # Markdown 报告生成
├── output/                    # 分析报告输出目录
└── cache/                     # 临时文件缓存
```

## 依赖

- Python 3.10+
- yt-dlp
- openai-whisper
- opencv-python-headless
- moviepy
- jieba
- imageio-ffmpeg (提供 ffmpeg 二进制)
- openai (可选，LLM 增强)

## 输出示例

生成的报告包含：
1. 📊 综合爆款评分卡（五维度雷达图）
2. 📈 互动数据分析
3. 📝 文案结构拆解（钩子/节奏/情绪/CTA）
4. 🎬 视觉与剪辑分析
5. 🏷️ 标签与发布策略
6. 🧠 AI 深度洞察（可选）
7. 📄 完整转录文本
