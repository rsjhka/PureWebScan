PureWebScan
 
Web 指纹识别系统 | Python + FastAPI + Vue.js
 
<img width="1266" height="478" alt="1" src="https://github.com/user-attachments/assets/cae6d76a-ae1b-4587-9465-f78d0f5ccc96" />

 
核心功能
 
- 指纹扫描：支持 HTTP Headers、Cookies、HTML 源码、JS 变量、URL 路径多维度检测
- Wappalyzer 兼容：直接加载 Wappalyzer 官方 JSON 规则库，无需格式转换
- 批量并发扫描：自定义并发数，适配大规模资产探测场景
- 规则管理：在线查看、上传、编辑、删除自定义指纹规则
- 历史记录：永久留存扫描任务，随时回溯查看历史探测结果
- 开放 API：完整 RESTful 接口，可与渗透工具、资产平台快速集成
 
 
 
技术亮点
 
- 基于 FastAPI 异步架构，高并发、低延迟
- SQLAlchemy ORM 数据层，兼容 SQLite / PostgreSQL
- 前端 Vue3 + Element Plus，界面简洁流畅、易操作
- 自研 Wappalyzer 规则解析器，完美适配官方指纹库
- 跨平台一键启动，自动校验环境、安装依赖
 
 
 
技术栈
 
分类 技术选型 
后端 Python / FastAPI / SQLAlchemy / aiohttp 
前端 Vue.js 3 / TypeScript / Element Plus / Pinia 
数据库 SQLite（默认） 
规则格式 JSON（原生兼容 Wappalyzer） 
 
 
 
项目结构
 
plaintext
  
PureWebScan/
├── backend/           # Python 后端服务
│   ├── api/           # 接口路由管理
│   ├── core/          # 扫描引擎 & 指纹规则解析
│   ├── models/       # 数据库实体模型
│   └── schemas/       # 数据校验与序列化
├── frontend/          # Vue.js 前端页面
├── rules/             # 指纹规则库目录
├── data/              # 本地数据持久化存储
├── start.py           # 项目统一启动入口
└── start.sh           # Linux / macOS 启动脚本
 
 
 
 
使用方法
 
1. 一键启动项目
 
bash
  
python start.py
 
 
2. 浏览器访问
 
plaintext
  
http://localhost:9933

<img width="1267" height="485" alt="2" src="https://github.com/user-attachments/assets/c83949f0-abba-43cd-8b72-9c333dba6b19" />



<img width="1265" height="674" alt="4" src="https://github.com/user-attachments/assets/ec0e9619-1e2e-4802-8a5b-bf1a04804e38" />








 
 
 
