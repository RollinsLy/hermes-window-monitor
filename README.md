## hermes-window-monitor

中文 | [English](#english)

一个常驻置顶的小马栏，为每个打开着的
[Hermes](https://hermes-agent.nousresearch.com) 对话窗口养一匹小马，让你一眼看出
哪些会话在干活、哪些在等你输入。

> Hermes 在中文社区俗称"爱马仕"，用 Hermes 干活戏称"养马"——所以这里真的给你养马。

每个 Hermes 对话会话都跑在自己的终端窗口里。这个工具在屏幕角落放一条小栏，
每个窗口对应一匹马：

- **马在奔跑** — 该会话的 worker 进程正忙（在生成回复、跑工具、输出内容）。
- **马在吃草** — 空闲。这一轮已经结束，马低头啃草，轮到你出手了。

**点击任意一匹马**，就能把对应的终端窗口弹到最前面，方便你直接打字。当你同时开着
好几个 Hermes 窗口、分不清哪匹马对应屏幕上哪个窗口时，点一下它就跳到你眼前。

把鼠标悬停在马上，会显示 tooltip：profile 名、当前状态（奔跑/吃草）、终端标题、
窗口句柄，以及该会话里的进程 ID。

### 为什么按窗口分马

一个 Hermes 对话会话实际上是一条进程链：

```
hermes.exe（原生启动器）
  └─ python.exe（venv 转发层）
       └─ python.exe（uv cpython —— 真正干活、占内存的 worker）
```

它们共享同一个所属终端窗口。监控器会把每个 Hermes 进程一路往上找到它的
窗口所属祖先进程，再按那个窗口句柄（HWND）归组，所以 **一个终端窗口 = 一匹马**，
不管里面跑了多少个 python 进程。新开一个 Hermes 窗口会自动多出一匹马，关掉一个
窗口它的马就消失。

### 环境要求

- Windows
- Python 3.8+
- [`psutil`](https://pypi.org/project/psutil/)

`tkinter` 和 `ctypes` 是 Windows 上标准 CPython 安装自带的。

### 安装

```cmd
pip install -r requirements.txt
```

### 运行

```cmd
python hermes_monitor.py
```

或者双击 `run.bat`。

想让它启动时不弹出黑色控制台窗口，用 `pythonw`：

```cmd
pythonw hermes_monitor.py
```

### 配置

改 `hermes_monitor.py` 顶部的几个常量即可：

| 常量 | 默认值 | 含义 |
| --- | --- | --- |
| `CPU_ACTIVE_THRESHOLD` | `2.0` | worker CPU% 高于此值算"在活动"（马奔跑）。 |
| `IDLE_SECONDS` | `3.0` | 空闲超过此秒数，马转为吃草。 |
| `SCAN_INTERVAL_MS` | `1000` | 多久重新扫描一次进程并采样 CPU。 |
| `ANIM_INTERVAL_MS` | `80` | 多久推进一帧马的动画（越小越流畅）。 |
| `HORSE_SCALE` | `1.0` | 马的整体大小倍数。 |
| `RUN_CYCLE_FRAMES` | `8` | 一个奔驰步态循环的帧数（越小跑得越快）。 |
| `GRAZE_CYCLE_FRAMES` | `40` | 一个吃草低头/抬头循环的帧数。 |

颜色也可以改：`COLOR_HORSE`（奔跑的马）、`COLOR_HORSE_IDLE`（吃草的马）、
`COLOR_GRASS`（草）等常量都在文件顶部。

### 已知限制

- **"吃草"是空闲，不是崩溃。** 从进程外部无法区分"完成本轮、等你输入"和"卡死"——
  两者看起来都是 worker 空闲。马吃草就只表示*当前没在动*，而这恰好就是本工具围绕的
  "该你了"信号。
- **同 profile 多窗口。** 马按窗口分组，所以两个跑同一 profile 的窗口会显示两匹马，
  标签都是比如 `default`。用点击弹窗（或 tooltip 里的标题 / PID）来区分它们。
- **终端标题是 shell 当前显示的内容**，你跑别的命令时它会变；标题只在 tooltip 里
  显示，从不用来分组。

### 许可

MIT —— 见 [LICENSE](LICENSE)。

---

<a name="english"></a>
## hermes-window-monitor (English)

[中文](#hermes-window-monitor) | English

A tiny always-on-top bar that keeps one little horse per open
[Hermes](https://hermes-agent.nousresearch.com) chat window, so you can tell at
a glance which sessions are working and which are waiting for you.

> In the Chinese community Hermes is nicknamed "爱马仕" (Hermès); running tasks
> on it is jokingly called "养马" — raising horses. So this really does raise a
> horse for you.

Each Hermes chat session runs inside its own terminal window. This tool puts a
small draggable bar in the corner of your screen with one horse per window:

- **Galloping horse** — the session's worker process is busy (generating a
  reply, running tools, printing output).
- **Grazing horse** — idle. The turn is finished; the horse drops its head to
  nibble grass. It's your move now.

**Click any horse** to bring that terminal window to the foreground so you can
start typing into it. Handy when you juggle several Hermes windows and can't
tell which horse maps to which window on screen — just click and it jumps to you.

Hover a horse to see a tooltip with the profile name, current state
(running/grazing), terminal title, window handle, and the process IDs in that
session.

### Why group horses by window

A single Hermes chat session is actually a chain of processes:

```
hermes.exe (native launcher)
  └─ python.exe (venv shim)
       └─ python.exe (uv cpython — the real worker, holds the memory)
```

All of them share one owning terminal window. The monitor walks each Hermes
process up to its window-owning ancestor and groups by that window handle
(HWND), so **one terminal window = one horse**, no matter how many python
processes live inside it. Open a new Hermes window and a new horse appears
automatically; close one and its horse disappears.

### Requirements

- Windows
- Python 3.8+
- [`psutil`](https://pypi.org/project/psutil/)

`tkinter` and `ctypes` ship with the standard CPython installer on Windows.

### Install

```cmd
pip install -r requirements.txt
```

### Run

```cmd
python hermes_monitor.py
```

Or double-click `run.bat`.

To launch it without a console window popping up, use `pythonw`:

```cmd
pythonw hermes_monitor.py
```

### Configuration

Edit the tunables near the top of `hermes_monitor.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `CPU_ACTIVE_THRESHOLD` | `2.0` | Worker CPU% above this counts as "active" (horse gallops). |
| `IDLE_SECONDS` | `3.0` | Idle longer than this and the horse starts grazing. |
| `SCAN_INTERVAL_MS` | `1000` | How often processes are rescanned and CPU sampled. |
| `ANIM_INTERVAL_MS` | `80` | How often the horse animation advances one frame (smaller = smoother). |
| `HORSE_SCALE` | `1.0` | Overall horse size multiplier. |
| `RUN_CYCLE_FRAMES` | `8` | Frames in one gallop stride (smaller = faster run). |
| `GRAZE_CYCLE_FRAMES` | `40` | Frames in one head-down/head-up graze bob. |

Colors are tweakable too: `COLOR_HORSE` (galloping), `COLOR_HORSE_IDLE`
(grazing), `COLOR_GRASS`, etc. are all near the top of the file.

### Known limits

- **"Grazing" means idle, not crashed.** From outside the process there is no
  way to tell "finished its turn and waiting for you" apart from "hung". Both
  look like an idle worker. A grazing horse simply means *not currently doing
  anything*, which is exactly the "your move" signal this tool is built around.
- **Same profile, multiple windows.** Horses are grouped by window, so two
  windows running the same profile show two horses both labelled e.g.
  `default`. Use the click-to-focus action (or the tooltip's title/PIDs) to tell
  them apart.
- **Terminal title is whatever the shell shows** and may change as you run other
  commands; it is shown only in the tooltip, never used for grouping.

### License

MIT — see [LICENSE](LICENSE).
