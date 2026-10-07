# Resin MeasureWare 产线部署与使用指南

## 一、打包构建（开发者）

```bash
# 在项目根目录执行
.venv/Scripts/pyinstaller ResinMeasureWare.spec

# 输出文件：dist/ResinMeasureWare.exe （约 75MB，单文件免安装）
```

> 如需重新构建，先删除 `build/` 和 `dist/` 目录以确保干净构建。

---

## 二、产线部署步骤

### 2.1 目标机环境要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Windows 10 / 11（64 位） |
| 内存 | 4 GB 以上 |
| 磁盘 | 500 MB 可用空间（含数据存储） |
| 网络 | 与 LJ-X8000 设备同一网段，TCP 可达 |
| 运行库 | 无需安装 Python 或任何依赖（已打包为独立 exe） |

### 2.2 目录结构

将以下文件放到目标机器的同一目录下（例如 `D:\ResinMeasureWare\`）：

```
D:\ResinMeasureWare\
├── ResinMeasureWare.exe    ← 主程序（双击运行）
├── config.json             ← （可选）配置文件，见 2.4 节
├── logs\                   ← （自动创建）日志目录
│   └── YYYY\
│       └── MM\
│           └── YYYYMMDD.log
├── measureware.db          ← （自动创建）SQLite 数据库
└── datasheets\             ← （自动创建）导出数据目录
    └── YYYY\
        └── MM\
            ├── OK\
            │   └── batch_xxx.csv
            └── NG\
                └── batch_xxx.csv
```

**部署只需 `ResinMeasureWare.exe` 这一个文件**，其余目录和文件均由程序自动创建。

### 2.3 首次启动检查

1. 双击 `ResinMeasureWare.exe`
2. 程序自动创建 `measureware.db` 数据库（含默认配置）
3. 确认窗口正常显示，无错误弹窗
4. 进入 **设置 → 设备配置**，设置 LJ-X8000 的 IP 地址和端口

### 2.4 配置说明

所有配置存储在 `measureware.db`（SQLite）中，通过程序 GUI 设置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| IP 地址 | LJ-X8000 控制器的 IP | 192.168.0.1 |
| 命令端口 | 无协议 TCP 接收端口 | 8501 |
| 提取模式 | ROI 数据提取方式 | 固定区域 |
| ROI 起始点 | 感兴趣区域起点 | 0 |
| ROI 结束点 | 感兴趣区域终点 | 511 |

> **批量部署**：在一台机器上配置好 `measureware.db`，复制到其他机器即可。

---

## 三、产线操作流程

### 3.1 日常开机

1. 确认 LJ-X8000 控制器已通电、网络已连接
2. 双击 `ResinMeasureWare.exe` 启动程序
3. 程序界面显示后，检查底部日志面板是否显示"应用程序已启动"

### 3.2 测量操作

1. **填写工单信息**：批号、品名、检测序号
2. **选择基准**：从基准库中选择对应产品的基准值（或新建基准）
3. **点击"开始测量"**：程序连接 LJ-X8000 并开始接收数据
4. **实时查看**：图表区显示测量曲线，数据表逐点更新
5. **自动判定**：测量完成后，程序自动根据基准值 ± 公差判定 OK/NG
6. **查看结果**：结果面板显示最大值、判定结果

### 3.3 数据导出

- **单个批次**：在结果面板点击"导出"，选择保存位置（CSV 格式）
- **历史数据**：通过历史查询选择会话并导出
- **自动保存**：每次测量数据自动存入 `datasheets/` 目录

---

## 四、维护与排错

### 4.1 日志查看

日志文件位置：`logs/YYYY/MM/YYYYMMDD.log`

可通过程序内的 **日志面板** 实时查看，也可用记事本直接打开日志文件。

### 4.2 常见问题

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| 程序无法启动 | 缺少 VC++ 运行库 | 安装 [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| "TCP 连接失败" | 设备 IP/端口配置错误 | 检查设置中的 IP 地址和端口 |
| "TCP 连接失败" | 网络不通 | ping 设备 IP，检查网线/交换机 |
| 无法解析数据 | 无协议模式未启用 | 在 LJ-X8000 设置中开启无协议 TCP 输出 |
| 程序卡顿 | 数据库文件过大 | 定期备份后清理 `measureware.db` |
| 杀毒软件误报 | exe 未签名 | 将程序目录加入白名单 |

### 4.3 数据库备份

建议每日/每周备份 `measureware.db`：

```batch
:: backup.bat - 加入 Windows 计划任务
copy /Y "D:\ResinMeasureWare\measureware.db" "D:\Backup\measureware_%date:~0,4%%date:~5,2%%date:~8,2%.db"
```

### 4.4 程序更新

1. 关闭正在运行的程序
2. 备份 `measureware.db`（保留历史数据）
3. 替换 `ResinMeasureWare.exe` 为新版本
4. 重新启动程序

---

## 五、高级配置

### 5.1 开机自启动

将快捷方式放入启动文件夹：

```batch
:: 创建快捷方式后放入
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

### 5.2 无人值守运行

如需无 GUI 交互的自动化运行，可联系开发团队提供命令行版本。

### 5.3 多台产线部署

每台产线工位独立部署一份程序，互不影响。如需统一管理测量数据，可配置网络共享路径存储 datasheets 和数据库（联系开发团队定制）。
