# Resin MeasureWare - 树脂测量数据监测软件

基于 Python + PySide6 的树脂测量数据监测软件，通过 Ethernet 网口与基恩士 LJ-X8000 系列 2D/3D 线激光测量仪控制器通信，实现作业员录入信息、测量数据的实时采集、可视化展示、最大值比对及 OK/NG 判定。

## 技术栈

| 组件 | 技术方案 | 选型理由 |
|------|----------|----------|
| GUI 框架 | PySide6 | Qt 官方 Python 绑定，与 QtCharts 无缝集成 |
| 图表模块 | QtCharts | 原生 GUI 集成、硬件加速渲染、内置交互功能 |
| 数据库 | SQLite + SQLAlchemy | 轻量级、无需独立服务器，ORM 简化数据操作 |
| 网络通信 | LJXAwrap.py | 基恩士官方通信库 |
| 数据处理 | pandas / numpy | 高效处理批量测量数据 |
| 架构模式 | MVC | 分离数据、界面与逻辑，提升可维护性 |

## 项目结构

```
MeasureWare/
├── main.py                              # 应用程序入口
├── LJX8_IF.dll                          # 基恩士通信 DLL (不修改)
├── LJXAwrap.py                          # 基恩士官方 Python 封装 (不修改)
├── sample_HowToCallFunctions.py         # 官方示例 - API 调用参考
├── sample_ImageAcquisition.py           # 官方示例 - 高速采集参考
├── README.md                            # 本文件
├── 开发文档.md                           # 开发需求文档
│
├── config/                              # 配置层
│   ├── app_settings.py                  # 应用设置 (IP/端口/提取参数)
│   └── logging_config.py                # 双通道日志 (文件 + GUI 信号)
│
├── models/                              # 数据模型层 (SQLAlchemy ORM)
│   ├── database.py                      # 数据库引擎、会话工厂、初始化
│   ├── settings_model.py                # DeviceConfig - 设备配置 (单例)
│   ├── baseline.py                      # ProductBaseline - 品名基准值
│   └── measurement.py                   # MeasurementSession / MeasurementPoint
│
├── controllers/                        # 控制器层
│   ├── device_controller.py            # LJXAwrap 同步封装 (在 Worker 线程运行)
│   ├── measurement_controller.py       # 测量状态机：会话生命周期/最大值/判定
│   ├── baseline_controller.py          # 品名基准值 CRUD
│   └── export_controller.py            # CSV 导出
│
├── workers/                            # 后台工作线程
│   ├── device_worker.py                # 真实设备采集循环 (QThread)
│   └── simulation_worker.py            # 仿真设备 - 离线开发/测试
│
├── views/                              # 视图层 (PySide6 GUI)
│   ├── main_window.py                  # 主窗口：菜单栏 + 面板组合 + 信号连接
│   ├── job_info_panel.py               # 作业信息录入面板
│   ├── measurement_chart_view.py       # 实时折线图 (QtCharts)
│   ├── measurement_table_view.py       # 可编辑测量数据表
│   ├── result_panel.py                 # OK/NG 判定结果面板
│   ├── log_panel.py                    # 滚动日志面板
│   ├── settings_dialog.py              # 通讯/提取设置对话框
│   └── baseline_dialog.py              # 品名基准值管理对话框
│
├── utils/                              # 工具模块
│   ├── profile_processor.py            # 从3200点轮廓提取标量值
│   └── csv_writer.py                   # pandas CSV 导出 (UTF-8-BOM)
│
└── resources/                           # 资源文件
    └── style.qss                        # 全局 Qt 样式表
```

## 系统架构

采用 **MVC (Model-View-Controller)** 架构模式：

```
┌─────────────┐     信号/槽      ┌─────────────┐     ORM      ┌─────────────┐
│   View      │ ◄──────────────► │ Controller  │ ◄──────────► │   Model     │
│  (PySide6)  │                  │  (逻辑层)    │              │ (SQLAlchemy)│
└─────────────┘                  └──────┬──────┘              └─────────────┘
                                        │
                                        │ QThread
                                        ▼
                                 ┌─────────────┐
                                 │   Worker    │
                                 │ (采集循环)   │
                                 └──────┬──────┘
                                        │ LJXAwrap
                                        ▼
                                 ┌─────────────┐
                                 │  LJ-X8000   │
                                 │  控制器     │
                                 └─────────────┘
```

## 核心功能

### 1. 作业信息录入
- 批号、品名（下拉自动补全，关联基准值表）、检测序号、目标测量点数
- 测量开始/停止/CSV 导出按钮
- 测量中自动锁定输入控件

### 2. 设备通信
- 基于基恩士官方 `LJXAwrap.py` 通信库
- 支持 Ethernet 连接/断开、测量启停、Profile 单次读取
- 所有通信在 QThread 后台线程执行，不阻塞 GUI

### 3. 数据采集与存储
- 采集流程：录入信息 → 点击开始 → 后台轮询 GetProfile → 提取标量值 → 存入数据库
- 每条产品测量 200-300 个点位（可配置）
- 所有点位数据持久化到 SQLite，支持查询和 CSV 导出

### 4. 实时图表
- QtCharts 折线图实时更新测量值
- 红色散点标记最大值位置
- QTableView 展示全部点位数据，支持双击手动修改
- 手动修改后自动重算最大值和判定结果

### 5. 比对判定
- 最大值与对应品名的基准值 ± 上下公差比对
- 绿色 **OK**（合格）/ 红色 **NG**（不合格）/ 灰色 **--**（未设置基准值）

### 6. 日志记录
- 主界面滚动日志面板，实时显示关键操作日志
- 后台 `RotatingFileHandler` 自动轮转写入 `logs/app.log`（5MB × 3 备份）

### 7. 软件参数配置
- **通讯设置**：IP 地址（四段）、命令端口、高速数据端口
- **提取设置**：提取模式（最大值/平均值）、ROI 区域（X 起始/结束索引）
- **品名基准值管理**：增删改查表格，支持行内编辑，品名唯一性校验

## 数据库设计

### device_config（设备配置，单例）
| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| ip_octet1~4 | INTEGER | 192,168,0,1 | IP 地址四段 |
| command_port | INTEGER | 24691 | 命令端口 |
| high_speed_port | INTEGER | 24692 | 高速数据端口 |
| extraction_mode | VARCHAR | max | 提取模式 |
| extraction_roi_start | INTEGER | 0 | ROI 起始 X 索引 |
| extraction_roi_end | INTEGER | 3199 | ROI 结束 X 索引 |

### product_baselines（品名基准值）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| product_name | VARCHAR UNIQUE | 品名（唯一） |
| baseline_value | FLOAT | 基准值 (mm) |
| tolerance_upper | FLOAT | 上公差 (mm) |
| tolerance_lower | FLOAT | 下公差 (mm) |

### measurement_sessions（测量任务）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| batch_number | VARCHAR | 批号 |
| product_name | VARCHAR | 品名 |
| inspection_sequence | VARCHAR | 检测序号 |
| baseline_value | FLOAT | 基准值快照 |
| max_measured_value | FLOAT | 所有点位最大值 |
| judgment | VARCHAR | OK / NG / -- |
| point_count | INTEGER | 点位数量 |

### measurement_points（测量点位）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| session_id | INTEGER FK | 关联 measurement_sessions |
| point_index | INTEGER | 点位序号 (1-based) |
| x_position | FLOAT | X 坐标 (mm) |
| measured_value | FLOAT | 测量值 (mm) |

## 快速开始

### 环境要求
- Windows 10/11
- Python 3.11+
- 基恩士 LJ-X8000 系列控制器（可选，仿真模式无需硬件）

### 安装与运行

```bash
# 1. 进入项目目录
cd MeasureWare

# 2. 激活虚拟环境
.venv\Scripts\activate

# 3. 安装依赖（已安装可跳过）
pip install PySide6 SQLAlchemy pandas numpy

# 4. 运行程序
python main.py
```

首次运行会自动创建 `measureware.db` 数据库文件并初始化默认配置。

### 仿真模式

默认使用**仿真模式**，无需连接 LJ-X8000 硬件即可体验完整功能：
1. 输入批号、品名
2. 点击「开始测量」
3. 观察实时折线图更新和表格数据填充
4. 测量完成后查看最大值和判定结果

切换到实机模式：菜单栏 `设置 → 仿真模式 (点此切换实机模式)`。

### 实机模式使用流程

```
1. 连接 LJ-X8000 控制器电源和 Ethernet 网线
2. 确认控制器 IP 地址（默认 192.168.0.1）
3. 打开软件，在 设置 → 通讯设置 中配置匹配的 IP 和端口
4. 录入批号、品名等信息
5. 点击「开始测量」
6. 软件自动采集 200-300 个点位数据
7. 查看折线图、数据表和 OK/NG 判定
8. 点击「导出 CSV」保存数据
```

## 开发说明

### MVC 架构约定
- **Model**：纯数据层，不依赖 PySide6，只使用 SQLAlchemy
- **View**：纯 GUI 层，不直接操作数据库，通过信号与 Controller 通信
- **Controller**：业务逻辑层，协调 Model 和 Worker，通过 Qt 信号向 View 推送数据

### 线程模型
- 主线程：GUI 事件循环（PySide6）
- Worker 线程：设备通信和采集循环
- 跨线程通信仅使用 Qt 信号/槽（`Signal`/`Slot`），自动排队安全投递

### 关键文件说明
- `LJXAwrap.py` / `LJX8_IF.dll`：基恩士官方通信库，**请勿修改**
- `sample_HowToCallFunctions.py`：官方 API 调用示例，包含所有可用函数
- `sample_ImageAcquisition.py`：高速批量采集示例（图像模式）
- `workers/simulation_worker.py`：仿真 Worker，与真实 Worker 共享相同的信号接口，可无缝切换

## License

本项目使用基恩士 `LJXAwrap.py` 通信库（Copyright (c) 2021 KEYENCE CORPORATION）。
