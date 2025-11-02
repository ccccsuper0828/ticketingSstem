# 票务管理系统后端（FastAPI + MySQL）

一个“大骨架”的 FastAPI 项目：包含分层目录、版本化 API、Alembic 与 Docker，便于扩展与协作（不含业务代码）。

## 快速开始

### 1) 创建并激活虚拟环境
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

如遇提示 `email-validator is not installed`，可手动补装（任选其一或都执行）：
```bash
pip install 'pydantic[email]'
pip install email-validator
```

### 2) 配置环境变量
```bash
cp .env.example .env
```
按需修改 `.env` 中数据库连接信息。

### 3) 创建数据库（可选）
```sql
CREATE DATABASE ticketing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4) 启动服务
```bash
uvicorn app.main:app --reload
# 文档: http://127.0.0.1:8000/docs
# 健康: http://127.0.0.1:8000/api/health
```

## 目录结构
```
.
├── app/
│   ├── main.py               # 入口文件，启动 FastAPI 应用
│   ├── api/                  # API 路由与视图（分版本）
│   │   ├── router.py         # 汇总各版本路由（含 /api/health）
│   │   └── v1/
│   │       ├── __init__.py   # v1 聚合路由
│   │       └── endpoints/    # v1 具体路由模块（占位，后续添加）
│   ├── core/                 # 核心功能（配置、安全等）
│   │   ├── config.py         # 读取 .env，提供 Settings
│   │   ├── database.py       # 对 db/ 的轻量封装（兼容导出 Base/get_db）
│   │   └── security.py       # 安全/鉴权相关（占位）
│   ├── db/                   # 数据库基础设置
│   │   ├── base.py           # SQLAlchemy Base 元数据
│   │   └── session.py        # Engine、SessionLocal、get_db 依赖
│   ├── models/               # ORM 模型（占位）
│   │   └── __init__.py
│   ├── schemas/              # Pydantic 模型（请求/响应，占位）
│   │   └── __init__.py
│   ├── crud/                 # 数据库 CRUD 封装（占位）
│   │   └── __init__.py
│   ├── tests/                # 测试（占位）
│   │   ├── __init__.py
│   │   └── test_main.py
│   └── utils/                # 工具函数（占位）
│       ├── __init__.py
│       └── utils.py
├── alembic/                  # 数据库迁移工具目录
│   ├── env.py
│   └── versions/
│       └── .keep
├── alembic.ini               # Alembic 配置
├── Dockerfile                # Docker 容器配置
├── .env.example              # 环境变量示例
├── .gitignore
├── requirements.txt
└── README.md
```

## 各目录/文件用途
- **app/**: 项目的主目录，包含所有应用相关代码。
  - **main.py**: 项目的入口文件，启动 FastAPI 应用。
  - **core/**: 核心功能，如配置、安全等。
  - **api/**: API 路由和视图，分版本管理（当前提供 v1 占位）。
  - **models/**: 数据库模型（ORM）。
  - **schemas/**: 数据模型，用于请求和响应的验证（Pydantic）。
  - **crud/**: 数据库操作封装（创建、读取、更新、删除）。
  - **db/**: 数据库相关设置和会话管理（Base/Engine/Session）。
  - **tests/**: 测试代码。
  - **utils/**: 工具函数和公用模块。
- **.env / .env.example**: 环境变量文件，存放敏感信息（如数据库连接字符串）。
- **alembic/**: 数据库迁移工具 Alembic 的配置目录，`versions/` 存放迁移文件。
- **alembic.ini**: Alembic 配置文件，`script_location` 指向迁移目录；`sqlalchemy.url` 留空，由 `alembic/env.py` 从应用设置动态注入。
- **requirements.txt**: 项目依赖列表。
- **Dockerfile**: Docker 配置文件，用于容器化部署。
- **README.md**: 项目说明文件（当前文档）。
