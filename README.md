# ulearning-questiontrain-export

 从 **优学院 (DGUT)** 的「题库训练（Question Train / Practice）」页面导出题目，并整理为 **佛脚刷题** 所需的 JSON 格式（格式定义见 `tmpl.jsonc`）。

> 说明（关于“官方站/学校专线”的差异）：
>
> - 本仓库默认适配的是 **东莞理工（DGUT）专属线路**：`https://lms.dgut.edu.cn/utest/`（页面）与 `https://lms.dgut.edu.cn/utestapi/`（接口）。
> - **优学院官方站**（`www.ulearning.cn`）与其他学校通常属于“同一套产品、多租户/多实例部署”。接口的**业务逻辑大概率相似**（例如同样存在 `answerSheet/questionList/answer`），但 **域名、路径前缀、鉴权 cookie 名称** 可能不同。
> - 因为我无法保证官方站与 DGUT 的路径一模一样，所以 README 里把“怎么定位 base URL 与关键接口”的方法写得更详细，方便你或其他学校同学进行二次开发。
> - 应该不是因为我懒得写

 本项目提供两条使用路线：

 - **路线 A：本地 Python 导出器**
   - 适合：可重复运行、自动化、归档、批量导出。
 - **路线 B：油猴脚本（Tampermonkey）一键导出**
   - 适合：你已经在题目页面，直接点击按钮导出并下载 JSON，无需本地 Python 环境。

 > 免责声明：本项目仅用于导出你自己账号在平台上可访问的数据，并进行格式整理。请遵守学校与课程平台的使用规范。

 ---

 ## 1. 输出格式（佛脚刷题 JSON）

 目标格式在 `tmpl.jsonc` 中定义，整体是一个数组（题目按顺序排列）。示例：

 - 选择题：
   - 字段：`题型`、`题干`、`选项`、`答案`、`解析`
 - 判断题：
   - 字段：`题型`、`题干`、`答案`、`解析`
 - 填空题：
   - 字段：`题型`、`题干`（答案用 `{}` 括起来嵌入题干）、`解析`
 - 问答题：
   - 字段：`题型`、`题干`、`答案`、`解析`

 当前实现规则（与 Python 和 Userscript 的逻辑一致）：

 - **选择题**：
   - 选项会输出成 `"A. xxx"`、`"B. xxx"`…
   - 答案会合并成字符串，例如 `"AC"`。
 - **判断题**：
   - 若平台答案为 `A/B`，会尽量映射成 `正确/错误`。
 - **填空题**：
   - 会尝试把题干中的空（`____`、`()、【】、[]`）按顺序替换成 `{答案}`。
   - 若题干找不到空位，会把 `{答案}` 追加到题干末尾。
 - **解析**：
   - 当前输出为空字符串（因为在我们抓到的接口响应里没有解析字段；后续若发现解析 API，可扩展）。

 ---

 ## 2. 项目原理

 ### 2.1 题目不是写死在 HTML 里

 你在浏览器里看到的题目，表面上像在页面 HTML 里，但其实平台是 SPA：

 - 前端页面加载后会调用后端接口拿到 **JSON 题目数据**。
 - 再由前端把 JSON 渲染成你看到的题干/选项。

 因此：**最稳定的导出方式不是去“扒 HTML”，而是复用浏览器已经请求过的 API**。

 ### 2.2 从 HAR（网络记录）定位到核心 API

使用 `F12` 刷新一下，在网络活动中可以看到题库训练页面的关键接口都在：

 `https://lms.dgut.edu.cn/utestapi/`

 核心需要两个接口：

 - **答题卡（答案/总题数/题目 ID 列表）**
   - `GET /questionTraining/student/answerSheet`
   - 作用：拿到 `total`（总题数）以及每道题的 `id -> answer` 映射。
 - **题目详情列表（分页）**
   - `GET /questionTraining/student/questionList`
   - 作用：分页拿到题干、选项等信息。

 这两个接口都需要参数：

 - `qtId`：题库训练 ID
 - `ocId`：课程/班级 ID
 - `qtType`：训练类型（通常为 `1`）
 - `traceId`：用户 ID（通常是 cookie `USERINFO.userId`）
 - `pn/ps`：页码/每页数量（仅 `questionList` 需要）

 还需要登录态：

 - `Authorization` 请求头（通常来自 cookie `AUTHORIZATION` 或 `token`）
 - 同域 cookie（浏览器里天然具备；Python 版本通过 cookie 文件/环境变量提供）

 ### 2.5 适配“官方站/其他学校域名”的思路（迁移指南）

 如果你使用的不是 `lms.dgut.edu.cn`（比如官方站 `www.ulearning.cn` 或其他学校域名），建议按下面流程迁移：

 1. 打开题库训练页面，按 `F12` -> Network，刷新页面。
 2. 在 Network 里搜索关键词：
    - `utestapi` 或 `answerSheet` 或 `questionList`
 3. 记录你看到的接口基址（base URL），通常形态类似：
    - `https://<your-domain>/utestapi/`
    - 或 `https://<your-domain>/<prefix>/utestapi/`
 4. 验证以下接口是否存在（路径可能一致/也可能需要微调）：
    - `GET /questionTraining/student/answerSheet`
    - `GET /questionTraining/student/questionList`
    - `POST /questionTraining/student/answer`（用于拿 `result.correctAnswer`）
 5. 验证鉴权方式：
    - 请求头里是否需要 `Authorization`（以及是否需要 `Bearer xxx`）
    - cookie 里是否仍然有 `USERINFO.userId`（我们用它当 `traceId`）

 只要你能在 Network 里看到这些请求成功（HTTP 200 + JSON `code` 正常），就基本可以把本项目的 `API_BASE` 与 cookie 解析逻辑迁移过去。

 ### 2.3 导出流程（我们的“思维”就是这条流水线）

 1. 从页面/配置中拿到：`qtId / ocId / qtType / traceId / Authorization`
 2. 调用 `answerSheet`：
    - 得到 `total` 与题目答案映射（按题目 `id` 关联）
 3. 根据 `total` 计算页数，循环调用 `questionList`：
    - 每页返回 `trainingQuestions`
    - 把答案映射合并到题目对象上
 4. 把平台题目 JSON 转成佛脚刷题 JSON
 5. 写出 `questions.json` / 或浏览器触发下载

 ### 2.4 为什么题干里会有 `<br/>`（以及我们怎么处理）

 平台返回的题干/选项是富文本（HTML），例如：

 - `...重大命<br />题...`

 如果导出时原样保留，阅读与搜索体验都会很差。

 因此我们在导出时做一次“HTML -> 纯文本”清洗：

 - `<br>` / `<br/>` / `<br />`：转换成换行 `\n`
 - `</p>` / `</div>` / `</li>` / `</tr>`：转换成换行 `\n`
 - 其余标签：直接移除
 - `&nbsp;` 等 HTML 实体：解码成正常字符

 性能方面：清洗是一次性线性扫描（`O(n)`），相对网络请求耗时可以忽略；并且文本更干净后通常更利于搜索。

 ---

 ## 3. 配置来源与优先级（为了用户方便）

 为了让用户尽量少操作，本项目支持 **三种来源** 的信息合并，优先级从高到低：

 1. **cookie 文件（`cookie.json` / `cookie.jsonc`）**（最高优先级）
 > 建议在浏览器的拓展商店搜索"cookie editor", 然后 Export Json
    - 提供：
      - `AUTHORIZATION`（从 cookie `AUTHORIZATION` 或 `token`）
      - `USER_ID`（从 cookie `USERINFO` / `USER_INFO` 解析 `userId`）
    - 若 cookie 和 `.env` 冲突：**以 cookie 为准**。
    - 推荐用户手动在根目录放置：`cookie.json`（纯 JSON）。
    - `cookie.jsonc` 仅作为演示文件(jsonc:json+comment(允许注释(coomment)))。

 3. **`.env` 文件**
    - 用户可以手动填写：`AUTHORIZATION / USER_ID / QT_ID / OC_ID / QT_TYPE`。

 4. **练习链接 `PRACTICE_URL`**
    - 只负责从链接中解析：`QT_ID / OC_ID / QT_TYPE`。
    - 示例：
      - `https://lms.dgut.edu.cn/utest/index.html?v=1765875491045#/questionTrain/practice/2674/134202/1`

 自动探测 cookie 文件（当你不显式指定时）：

 - 先找根目录 `cookie.json`
 - 再找根目录 `cookie.jsonc`

 ---

 ## 4. Python 导出器（推荐路线）

 ### 4.1 目录结构

 ```
 .
 ├── main.py                   # 根目录启动入口（建议使用）
 ├── python/
 │   ├── client.py             # 调用 utestapi
 │   ├── config.py             # 合并 cookie/.env/url 配置
 │   ├── formatter.py          # 转佛脚刷题 JSON
 │   └── exporter.py           # 写文件导出
 ├── .env.example              # 环境变量示例
 ├── tmpl.jsonc                # 目标 JSON 格式说明
 └── UserScript/_userscript.js # 油猴脚本
 ```

 ### 4.2 安装依赖

 本项目使用 `uv` 管理依赖：

 ```bash
 uv sync
 ```

 ### 4.3 使用方式（推荐顺序）

 #### 方式 1：cookie.json + 链接（最省事）

 1) 浏览器导出 cookie 为 `cookie.json`（推荐）

 - 放到项目根目录（与 `main.py` 同级）

 2) 复制你当前题目页面的链接（practice URL）

 3) 运行：

 ```bash
 uv run python main.py --url "https://lms.dgut.edu.cn/utest/index.html?v=1765875491045#/questionTrain/practice/2674/134202/1" --txt
 ```

 #### 方式 1.1：导出“标准答案版”（默认行为，会自动答题）

 通过 一些答题时候的网络活动 我们确认：提交答题接口会在响应中返回 `correctAnswer`（标准答案）。
 因此本项目将“标准答案导出”作为默认行为：程序会对每道题提交一个“随便答案”，从响应中收集 `correctAnswer`，并将导出的 `答案` 字段替换为标准答案。

 重要提示：

 - **`--correct` 会写入你的答题记录**（平台会认为你做过这些题，正确率可能变化）。
 - 如果你只想先验证功能，可以用 `--correct-limit` 限制只提交前 N 题。

 示例：

 ```bash
 # 仅测试前 20 题
 uv run python main.py --url "https://lms.dgut.edu.cn/utest/index.html?v=...#/questionTrain/practice/2674/134202/1" --correct-limit 20

 # 全量导出标准答案（会对全部题目提交一次答案）
 uv run python main.py --url "https://lms.dgut.edu.cn/utest/index.html?v=...#/questionTrain/practice/2674/134202/1" --txt
 ```

 #### 方式 1.2：导出“用户作答答案版”（--user-answer）

 如果你想导出用户作答答案（不提交答案，不保证有值/不保证正确），可以使用 `--user-answer` 参数。

 示例：

 ```bash
 uv run python main.py --url "https://lms.dgut.edu.cn/utest/index.html?v=...#/questionTrain/practice/2674/134202/1" --user-answer --txt
 ```

 #### 方式 2：只用 .env（完全手动）

 1) 复制 `.env.example` 为 `.env`
 2) 填写 `AUTHORIZATION / USER_ID / QT_ID / OC_ID / QT_TYPE`
 3) 运行：

 ```bash
 uv run python main.py --txt
 ```

 #### 方式 3：同时用 cookie 与 .env（cookie 覆盖 .env）

 当你希望 `.env` 作为“默认值”，但又希望 cookie 更新后优先用 cookie：

 - 保留 `.env`
 - 放置/指定 `cookie.json`
 - 运行时 cookie 的 `AUTHORIZATION/USER_ID` 会覆盖 `.env`

 ### 4.4 输出文件

 默认输出到 `output/`：

 - `output/questions.json`：佛脚刷题 JSON（主产物）
 - `output/questions.txt`：可读文本（需要 `--txt`）
 - `output/questions_raw.json`：原始平台 JSON（需要 `--raw`）

 ---

 ## 5. 油猴脚本一键导出（无需本地 Python）

 文件：`UserScript/_userscript.js`

 ### 5.1 安装

 1) 安装 Tampermonkey
 2) 新建脚本，把 `UserScript/_userscript.js` 内容粘贴进去保存
 3) 打开题库训练页面（practice 页面）

 ### 5.2 使用

 页面右下角会出现按钮：`Export Questions JSON`

 点击后脚本会：

 - 从当前浏览器 cookie 自动拿 `Authorization` 和 `userId`
 - 调用 `answerSheet` + `questionList` 分页拉题目
 - 转成佛脚刷题 JSON
 - 触发下载文件：
   - `ulearning_{qtId}_{ocId}_{qtType}_questions.json`

 ### 5.3 常见问题

 - **按钮出现但报错 Missing Authorization cookie**
   - 说明你当前未登录或登录态失效；重新登录后刷新页面。
 - **报错 Not on practice page**
   - 说明当前页面 hash 不是 `#/questionTrain/practice/...`；请确保在题目训练页面。

 ---

 ## 6. 隐私与安全

 - `AUTHORIZATION` 和 cookie 相当于登录凭证，**不要提交到仓库**、不要发给他人。
 - 本仓库的 `.gitignore` 已忽略：`.env`、~~`cookie.jsonc`~~(优学院的信息暴露就暴露吧，能帮我写作业就再好不过了)、导出结果等。

 ---

 ## 7. 快速命令汇总

 - cookie + 链接导出：

 ```bash
 uv run python main.py --url "https://lms.dgut.edu.cn/utest/index.html?v=...#/questionTrain/practice/2674/134202/1" --txt
 ```

 - 手动 .env 导出：

 ```bash
 uv run python main.py --txt
 ```

