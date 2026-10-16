# 宿舍报修管理系统（Flask + MySQL + Bootstrap 5）

面向高校宿舍场景的报修管理平台，覆盖「学生报修 → 维修人员接单维修 → 学生评价 → 管理员统计管理」的完整闭环。
项目采用经典分层架构（视图层 / 业务层 / 数据访问层 / 基础设施层），代码注释详细，可直接作为软件工程课程设计提交。

## 一、技术栈

| 层次 | 技术选型 |
| --- | --- |
| 后端框架 | Python 3.10+ / Flask 3.1 |
| 数据库 | MySQL 8.0（PyMySQL 驱动，原生 SQL + 事务） |
| 前端 | Bootstrap 5.3 + Bootstrap Icons + 原生 JavaScript（已本地化，断网可用） |
| 密码安全 | Werkzeug PBKDF2-SHA256 加盐哈希（数据库不存明文密码） |
| 会话管理 | Flask Session + 角色装饰器（`login_required` / `role_required`） |

## 二、功能清单

### 1. 学生用户

- 账号注册（学号、姓名、手机号、宿舍号，含格式与唯一性校验）、登录、退出、修改密码与资料
- 提交报修工单：宿舍楼栋、宿舍号、故障类别、故障详细描述、联系电话，可上传最多 3 张现场图片
- 查看自己提交的全部工单，按状态（待受理 / 维修中 / 已完成）与关键词筛选，分页浏览
- 查看工单详情：报修信息、现场图片、维修进度时间线、维修备注
- 维修完成后对本次维修提交 1-5 星评分与文字评价（一个工单仅可评价一次）

### 2. 维修人员

- 账号登录（账号由管理员创建）、工作台统计（待受理 / 维修中 / 已完成 / 平均评分）
- 抢单大厅：查看全部未受理工单，支持关键词与故障类别筛选，一键接单
- 我的维修单：查看已接工单，按状态筛选
- 更新维修状态（维修中 / 已完成）并填写维修备注；标记完成后自动记录完成时间
- 查看学生对自己提交的评价

### 3. 管理员

- 账号登录、系统概览（工单总量、各状态数量、平均评分、平均维修时长、用户构成）
- 用户管理：新增、查看、删除学生 / 维修人员账号，重置用户密码（管理员账号受保护不可删除）
- 工单管理：按关键词、状态、故障类别、楼栋、提交时间范围、删除状态多条件检索；查看任意工单详情与完整流转日志；删除无效工单（逻辑删除，可恢复）
- 数据统计：状态分布、故障类别分布、楼栋分布、近 6 个月报修趋势、服务评分分布、维修人员工作量与评分排名
- 评价记录：查看全部学生评价

## 三、项目结构

```
manage/
├── run.py                      # 启动入口（python run.py）
├── init_db.py                  # 一键建库建表 + 初始数据（python init_db.py）
├── config.py                   # 全局配置（MySQL 连接、上传目录、分页等）
├── requirements.txt            # 依赖清单
├── .env.example                # 环境变量模板（可复制为 .env 覆盖默认配置）
├── sql/
│   └── schema.sql              # 数据库建表 SQL（含主键、外键、索引、注释、初始数据）
├── tools/
│   ├── smoke_test.py           # 端到端自检脚本（49 项断言）
│   └── seed_demo_data.py       # 演示数据生成 / 清理脚本
└── app/
    ├── __init__.py             # 应用工厂：注册蓝图、模板全局变量、错误处理
    ├── constants.py            # 角色 / 状态 / 楼栋 / 工种等常量
    ├── exceptions.py           # 业务异常 BusinessError
    ├── blueprints/             # 视图层：接收请求、调用服务层、渲染模板
    │   ├── main.py             # 首页与角色工作台
    │   ├── auth.py             # 注册 / 登录 / 退出 / 资料 / 改密
    │   ├── student.py          # 学生端
    │   ├── worker.py           # 维修端
    │   └── admin.py            # 管理端
    ├── services/               # 业务层：校验规则、状态流转、事务编排
    │   ├── auth_service.py     # 注册、登录、改密
    │   ├── user_service.py     # 管理员用户管理
    │   ├── order_service.py    # 工单提交 / 接单 / 进度更新 / 删除
    │   ├── review_service.py   # 维修评价
    │   ├── category_service.py # 故障类别
    │   └── stats_service.py    # 数据统计
    ├── dao/                    # 数据访问层：只写 SQL，不含业务规则
    │   ├── base.py             # 统一执行入口（支持复用事务游标）
    │   ├── user_dao.py
    │   ├── order_dao.py
    │   ├── review_dao.py
    │   ├── category_dao.py
    │   └── stats_dao.py
    ├── utils/                  # 基础设施层
    │   ├── db.py               # PyMySQL 请求级连接 + 事务上下文管理器
    │   ├── decorators.py       # 登录 / 角色校验装饰器
    │   └── helpers.py          # 工单号生成、图片上传、分页、脱敏
    ├── templates/              # Jinja2 模板（base.html + 各角色页面 + 宏 + 错误页）
    └── static/                 # 样式、脚本、本地化 Bootstrap 资源、上传目录
```

## 四、数据库设计

数据库名：`dorm_repair`（字符集 utf8mb4），共 6 张表，完整建表语句见 `sql/schema.sql`。

| 表名 | 说明 | 主要外键 |
| --- | --- | --- |
| `sys_user` | 用户表：学生 / 维修人员 / 管理员 | — |
| `fault_category` | 故障类别字典表 | — |
| `repair_order` | 报修工单主表 | `student_id` → `sys_user.id`；`worker_id` → `sys_user.id`；`category_id` → `fault_category.id` |
| `order_image` | 工单现场图片表（1 工单 : N 图片） | `order_id` → `repair_order.id`（级联删除） |
| `order_log` | 工单流转日志表（接单 / 备注 / 完成 / 评价轨迹） | `order_id` → `repair_order.id`（级联删除）；`operator_id` → `sys_user.id` |
| `repair_review` | 维修评价表（1 工单 : 1 评价） | `order_id` → `repair_order.id`（唯一 + 级联删除）；`student_id` → `sys_user.id` |

关键设计说明：

- 三类角色共用一张用户表，通过 `role` 枚举区分；`student_no`、`worker_no` 分别建立唯一索引，MySQL 允许多个 NULL 值，因此不会互相冲突。
- 工单状态使用 `ENUM('pending','processing','completed')`，配合 `accepted_at`、`completed_at` 记录关键时间点，可直接算出维修时长。
- `order_log` 保留每一次状态变更与维修备注，学生与管理员看到的「维修进度时间线」即来源于此。
- 无效工单采用逻辑删除（`is_deleted = 1`），既能满足「删除无效工单」的需求，又不破坏统计数据，还支持一键恢复。

## 五、运行步骤

### 1. 准备环境

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

确保本机 MySQL 8.0 服务已启动（Windows 下服务名为 `MySQL80`）。

### 2. 配置数据库连接

打开 `config.py`，确认以下配置与本机一致（当前已按本机填好）：

```python
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "Qiu_200604"     # 改成你自己的 MySQL 密码
MYSQL_DB = "dorm_repair"
```

也可以复制 `.env.example` 为 `.env` 并写入配置，`.env` 的优先级高于 `config.py` 默认值。

### 3. 初始化数据库（自动建库、建表、写入演示账号）

```bash
python init_db.py
```

看到「数据库初始化成功」即完成；如需清空重建可执行 `python init_db.py --reset`。
也可以直接在 MySQL Workbench 中打开并执行 `sql/schema.sql`。

### 4. 启动系统

```bash
python run.py
```

浏览器访问 <http://127.0.0.1:5000>

### 5. 演示账号（初始密码均为 123456）

| 角色 | 账号 | 说明 |
| --- | --- | --- |
| 管理员 | `admin` | 用户管理、工单管理、数据统计 |
| 维修人员 | `worker001` / `worker002` | 接单与更新维修进度 |
| 学生 | `student001` | 提交报修与评价 |

可选：执行 `python tools/seed_demo_data.py` 生成近 6 个月的演示工单数据（含 6 个学生账号
`demo_stu01`~`demo_stu06` 与 2 个维修账号 `demo_wrk01`、`demo_wrk02`），便于答辩时展示统计图表；
执行 `python tools/seed_demo_data.py --clear` 可清除演示数据。

## 六、业务流程与状态流转

```
学生注册登录 ──提交报修工单（含图片）──▶ 待受理 pending
                                            │ 维修人员接单（条件更新，防止重复抢单）
                                            ▼
                                        维修中 processing ──填写维修备注──┐
                                            │                            │（可多次补充）
                                            │ 维修人员标记完成            │
                                            ▼                            ▼
                                        已完成 completed ────────────────┘
                                            │ 学生提交 1-5 星评价（仅一次）
                                            ▼
                                      已评价（写入 repair_review + order_log）
```

关键业务规则（均在 `app/services/` 中实现并配有注释）：

1. 工单号由系统生成（`RX + 时间戳 + 随机数`），保证唯一。
2. 接单使用条件更新 `WHERE status = 'pending'`，影响行数为 0 说明已被抢单，事务回滚并提示。
3. 提交工单时「工单主表 + 图片表 + 流转日志」在同一事务中写入；写库失败会自动清理已落盘的图片。
4. 只有工单所属学生可以评价、只有接单维修人员可以更新进度，越权操作被业务层拦截。
5. 已完成工单不可再次修改；未完成工单不允许评价；同一工单不可重复评价。
6. 删除工单采用逻辑删除并记录操作日志，学生与维修人员侧立即不可见，管理员可恢复。

## 七、验证方式

项目自带端到端自检脚本，会真实走一遍注册 → 报修 → 接单 → 维修 → 评价 → 管理员检索统计 → 删除恢复 → 权限校验，并在结束后自动清理测试数据：

```bash
python tools/smoke_test.py
```

预期输出：`通过：49 项    失败：0 项`。

## 八、常见问题排查

| 现象 | 原因与处理 |
| --- | --- |
| 启动后访问 500，提示「无法连接数据库」 | MySQL 服务未启动，或 `config.py` 中账号密码错误；先确认 `mysql -u root -p` 能登录 |
| `Access denied for user 'root'@'localhost'` | 密码不对，改 `config.py` 中的 `MYSQL_PASSWORD`（或写入 `.env`） |
| `Unknown database 'dorm_repair'` | 未初始化数据库，先执行 `python init_db.py` |
| `ModuleNotFoundError: No module named 'flask'` | 依赖未安装或未激活虚拟环境，执行 `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'pymysql'` | 单独执行 `pip install pymysql` |
| 端口 5000 被占用 | 修改 `run.py` 最后一行的 `port=5000` 为其它端口 |
| 页面样式丢失 | `app/static/vendor/` 下的 Bootstrap 资源被删除，重新下载或改用 CDN 地址 |
| 上传图片失败提示格式不支持 | 仅支持 png / jpg / jpeg / gif / bmp / webp，且单张不超过 5MB |

## 九、可扩展方向（答辩加分项）

- 接入邮件 / 短信通知，工单状态变更时提醒学生与维修人员
- 增加工单催单、超时预警（超过 24 小时未接单自动标黄）
- 故障类别与奖罚规则的后台配置化
- 统计数据导出为 Excel 报表
- 增加基于楼栋与工种的智能派单推荐
