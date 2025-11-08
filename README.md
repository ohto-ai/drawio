# Draw.io Enhanced Edition

一个增强版的Draw.io图表编辑器，支持网络拓扑分析、智能高亮管理和服务器端集成功能。

## 目录

- [功能特性](#功能特性)
- [服务器集成](#服务器集成)
- [JavaScript API](#javascript-api)
- [Python工具脚本](#python工具脚本)
- [安装和配置](#安装和配置)
- [使用示例](#使用示例)
- [开发指南](#开发指南)

## 功能特性

### 核心功能
- **图表加载管理**: 支持从URL动态加载DrawIO图表文件
- **编辑状态控制**: 灵活的只读/编辑模式切换
- **智能高亮系统**: 基于条件和指定的多重高亮管理
- **服务器集成**: 完整的HTTP服务器，支持静态文件服务和文件管理
- **网络拓扑分析**: 提取、分析和可视化网络连接关系

### 增强特性
- 条纹覆盖高亮管理器 (StripedOverlayManager)
- 网络环路检测和可视化
- 网表提取和CSV导出
- 随机拓扑生成工具
- 内置HTTP服务器，支持静态文件服务和文件管理
- 服务器端图表文件存储和访问

## 服务器集成

本项目提供了一个功能完整的HTTP服务器 (`server/server.py`)，支持静态文件服务和服务器端文件管理，为draw.io提供完整的Web应用托管解决方案。

### 服务器特性

#### 静态文件服务
- 完整的draw.io Web应用静态文件服务 (基于 `src/main/webapp` 目录)
- 自动为目录请求提供 `index.html`
- 正确的MIME类型检测和Content-Type头设置
- 路径遍历攻击防护

#### 服务器文件集成
- **新增 `/open/{filename}` 端点**：提供单个保存图表的访问
- **增强文件浏览器**：同时显示浏览器存储和服务器存储的文件
- **位置指示器**：区分浏览器和服务器文件
- **直接文件打开**：从draw.io界面直接打开服务器存储的图表
- 安全措施：包括路径遍历保护和文件类型验证

#### 可配置参数
- `--host`: 配置绑定主机 (默认: localhost)
- `--port`: 配置端口 (默认: 8080) 
- `--static-dir`: 配置静态文件目录 (默认: src/main/webapp)
- `--save-dir`: 配置上传目录 (默认: server/saved_files)

### API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 提供draw.io Web应用静态文件 |
| `/save` | POST | 保存图表文件到服务器 |
| `/list` | GET | 列出保存的文件及元数据 |
| `/open/{filename}` | GET | **新功能**: 打开指定的保存图表文件 |
| `/health` | GET | 健康检查 |

### 启动服务器

**基本用法:**
```bash
# 默认使用 - 在 localhost:8080 提供 src/main/webapp
python server/server.py
```

**自定义配置:**
```bash
# 监听所有接口
python server/server.py --host 0.0.0.0 --port 3000

# 自定义静态文件目录
python server/server.py --static-dir ./my-webapp --port 8080

# 自定义保存目录
python server/server.py --save-dir ./my-diagrams
```

### 文件管理工作流程

1. 用户在draw.io Web界面中创建图表
2. 使用内置保存功能将图表保存到服务器
3. 从"文件"→"打开"菜单访问浏览器存储和服务器存储的文件
4. 服务器文件有清楚标记，可直接点击打开
5. 服务器文件在浏览器会话和设备间持久化

**服务器日志示例:**
```
INFO:__main__:Server starting on localhost:8080
INFO:__main__:Static files served from: /path/to/src/main/webapp
INFO:__main__:Uploaded files will be saved to: /path/to/server/saved_files
INFO:__main__:Available endpoints:
INFO:__main__:  GET / - Serve static files from static directory
INFO:__main__:  POST /save - Save a file
INFO:__main__:  GET /health - Health check
INFO:__main__:  GET /list - List saved files
INFO:__main__:  GET /open/{filename} - Open a saved file
```

## JavaScript API

### 图表加载和管理

#### `loadGraphXML(url, readonly = false)`
从指定URL加载DrawIO图表文件。

**参数:**
- `url` (string): 图表文件的URL地址
- `readonly` (boolean, 可选): 是否以只读模式加载，默认为false

**返回值:**
- `Promise<LocalFile>`: 返回加载的LocalFile对象的Promise

**示例:**
```javascript
// 加载可编辑图表
window.ohtoai.loadGraphXML('demo/network.drawio.xml')
  .then(file => console.log('图表加载成功:', file.getTitle()))
  .catch(error => console.error('加载失败:', error));

// 加载只读图表
window.ohtoai.loadGraphXML('demo/readonly.drawio.xml', true);
```

### 编辑状态控制

#### `enableEditing()`
启用图表编辑功能。

**返回值:**
- `boolean`: 启用成功返回true，失败返回false

#### `disableEditing()`
禁用图表编辑功能，设置为只读模式。

**返回值:**
- `boolean`: 禁用成功返回true，失败返回false

#### `isEditingEnabled()`
检查当前图表编辑状态。

**返回值:**
- `boolean`: 编辑功能启用时返回true，否则返回false

**示例:**
```javascript
// 切换编辑状态
if (window.ohtoai.isEditingEnabled()) {
    window.ohtoai.disableEditing();
    console.log('已切换到只读模式');
} else {
    window.ohtoai.enableEditing();
    console.log('已启用编辑模式');
}
```

### 文件保存和库管理

#### `saveToServer(filename, successCallback, errorCallback)`
将当前图表保存到服务器。

**参数:**
- `filename` (string): 保存的文件名
- `successCallback` (function, 可选): 保存成功的回调函数
- `errorCallback` (function, 可选): 保存失败的回调函数

**示例:**
```javascript
window.ohtoai.saveToServer('my-diagram.drawio',
    function(data) {
        console.log('保存成功:', data.filename);
    },
    function(error) {
        console.error('保存失败:', error.message);
    }
);
```

#### `loadLibraryFromServer(libraryPath, successCallback, errorCallback)`
从服务器加载形状库文件到侧边栏。

**参数:**
- `libraryPath` (string): 服务器上库文件的路径
- `successCallback` (function, 可选): 加载成功的回调函数
- `errorCallback` (function, 可选): 加载失败的回调函数

**回调参数:**
- `successCallback(data)`: data包含 `{title, shapesCount, library}` 
- `errorCallback(error)`: error包含 `{message}` 

**示例:**
```javascript
window.ohtoai.loadLibraryFromServer('custom-shapes.xml',
    function(data) {
        console.log(`库 "${data.title}" 加载成功，包含 ${data.shapesCount} 个形状`);
    },
    function(error) {
        console.error('库加载失败:', error.message);
    }
);
```

### StripedOverlayManager 高亮管理器

一个功能强大的图表元素高亮管理系统，支持条件高亮和指定高亮两种模式。

#### 构造函数
```javascript
new StripedOverlayManager(graph, strokeWidth = 4)
```

**参数:**
- `graph` (mxGraph): mxGraph实例
- `strokeWidth` (number, 可选): 高亮边框宽度，默认为4

#### 主要方法

##### `addConditionalHighlight(id, callback, colors)`
添加基于条件判断的动态高亮。

**参数:**
- `id` (string): 高亮标识符，用于后续移除或更新
- `callback` (function): 判断函数，接受cell参数，返回boolean
- `colors` (string[]): 颜色组数组，用于循环动画显示

**返回值:**
- `boolean`: 添加成功返回true，参数无效返回false

##### `addSpecificHighlight(id, cells, colors)`
为指定的单元格添加高亮。

**参数:**
- `id` (string): 高亮标识符
- `cells` (object[]): 要高亮的单元格数组
- `colors` (string[]): 颜色组数组

**返回值:**
- `boolean`: 添加成功返回true，参数无效返回false

##### 其他方法
- `removeConditionalHighlight(id)`: 移除条件高亮
- `removeSpecificHighlight(id)`: 移除指定高亮
- `clearHighlight()`: 清除所有高亮
- `refresh()`: 刷新高亮显示
- `getConditionalHighlights()`: 获取所有条件高亮信息
- `getSpecificHighlights()`: 获取所有指定高亮信息

**使用示例:**
```javascript
// 创建高亮管理器
const graph = window.sb.editorUi.editor.graph;
const highlightManager = new StripedOverlayManager(graph);

// 添加条件高亮 - 高亮所有alarm属性为'1'的单元格
highlightManager.addConditionalHighlight('alarm_cells', 
    cell => {
        if (!cell || !cell.value) return false;
        return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
    }, 
    ['#ff0000', '#ffff00', '#ff8800']
);

// 刷新显示
highlightManager.refresh();

// 注意：系统会自动创建一个全局实例 window.ohtoai.stripedOverlayManager
// 可以直接使用：window.ohtoai.stripedOverlayManager.addConditionalHighlight(...)
```

## Python工具脚本

本项目包含多个强大的Python工具脚本，用于网络拓扑分析和可视化。

### terminal_data_model.py - 端子数据模型工具

从Excel文件加载端子连接数据并生成Draw.io格式的接线图。支持前端面板端子、后端装置和元件的可视化。

**新特性 (v1.0):**
- ✨ **互联类型支持**: 可在后端互联数据中指定连接类型（如"刀开关"、"LED"等）
- 🔧 **自动中间节点**: 当指定互联类型时，自动在连接中插入相应的图形元件
- 📊 **矩阵布局**: 支持装置组端子的二维矩阵布局
- 🎨 **丰富图形库**: 内置多种电气元件图形（开关、继电器、LED等）

**用法:**
```bash
python3 scripts/terminal_data_model.py
# 或在代码中使用
from terminal_data_model import TerminalDataModel
model = TerminalDataModel()
model.load_xlsxs(['data.xlsx'])
model.export_drawio_groups('output_dir')
```

**Excel数据表格式:**

1. **互联数据** (支持互联类型):
   - 设备编号: 机柜/设备标识
   - 互联起点: 连接起始端子
   - 互联终点: 连接目标端子
   - **互联类型** (新): 连接类型，如"刀开关"、"闭合开关"、"LED"等

2. **装置布局**:
   - 设备编号, 装置编号, 装置组编号, 布局端子

3. **元件数据**:
   - 设备编号, 元件编号, 元件类型, 元件端子

**支持的互联类型:**
- 刀开关 (knife switch)
- 闭合开关 (closed switch)
- 双刀开关 (double-pole switch)
- 压板 (pressure plate)
- LED (indicator light)
- *可通过修改 `COMPONENT_GRAPHICS` 添加自定义类型*

**示例:**
```bash
# 使用示例数据
python3 scripts/test_connection_types.py

# 查看示例文件
ls scripts/examples/connection_types_example.xlsx

# 生成的draw.io文件
ls scripts/examples/output/
```

详细文档请参考: [CONNECTION_TYPES.md](scripts/CONNECTION_TYPES.md)

### extract_netlist.py - 网表提取工具

从Draw.io XML文件中提取组件和连线信息，生成CSV格式的网表数据。

**用法:**
```bash
python3 scripts/extract_netlist.py [input_dir] [-o OUTPUT] [-v]
```

**参数:**
- `input_dir`: 包含.drawio.xml文件的目录 (默认: src/main/webapp/demo)
- `-o, --output`: CSV文件输出目录 (默认: netlist_output)
- `-v, --verbose`: 启用详细输出

**输出文件:**
- `components.csv`: 组件信息，包含位置和属性
- `wires.csv`: 连线连接信息
- `summary_components.csv`: 跨页面的所有组件汇总
- `summary_wires.csv`: 所有连线连接汇总

**示例:**
```bash
# 提取demo目录中的网表
python3 scripts/extract_netlist.py src/main/webapp/demo -o network_data

# 输出示例
Vertices:
C1 CMP1 {'alarm': '1', 'prop2': '3', 'group_id': 'G1', 'image_id': 'pic1'}
C2 CMP2 {'alarm': '2', 'prop2': '2', 'group_id': 'G2', 'image_id': 'pic2'}
...

Edges:
C1 -> C2 (edge W1)
C2 -> C3 (edge W2)
...
```

### detect_cycles.py - 环路检测工具

检测网表中的环路并为每个环路生成独立的Draw.io XML文件。

**用法:**
```bash
python3 scripts/detect_cycles.py [input_dir] [-o OUTPUT] [-v]
```

**参数:**
- `input_dir`: 包含汇总CSV文件的目录 (默认: netlist_output)
- `-o, --output`: 环路XML文件输出目录 (默认: cycles_output)
- `-v, --verbose`: 启用详细输出

**特性:**
- 保持原始组件尺寸和属性
- 圆形布局展示环路
- 生成可直接在Draw.io中打开的XML文件

**示例:**
```bash
# 先提取网表
python3 scripts/extract_netlist.py src/main/webapp/demo -o netlist_out

# 然后检测环路
python3 scripts/detect_cycles.py netlist_out -o cycles_out
```

### gen_graph.py - 图表生成工具

根据CSV数据生成Draw.io XML格式的示意图。

**功能:**
- 支持多种组件形状 (point, line, face, mark)
- 正交连线样式
- 自定义属性支持
- 智能端口定位

**示例:**
```bash
python3 scripts/gen_graph.py
# 读取 components.csv 和 wires.csv，生成 schematic.drawio.xml
```

### random_topo.py - 随机拓扑生成器

生成随机网络拓扑的测试数据。

**生成文件:**
- `components.csv`: 随机组件数据
- `ports.csv`: 端口信息
- `wires.csv`: 连线数据

**示例:**
```bash
python3 scripts/random_topo.py
# 在 test_drawio 目录生成随机测试数据
```

## 安装和配置

### 环境要求
- Python 3.6+
- 现代Web浏览器 (Chrome, Firefox, Safari, Edge)

### 安装步骤

1. **克隆仓库:**
```bash
git clone https://github.com/ohto-ai/drawio.git
cd drawio
```

2. **配置Python环境:**
```bash
# 安装依赖 (如果有requirements.txt)
pip3 install -r requirements.txt
```

3. **启动服务器:**
```bash
# 使用内置服务器 (推荐)
python server/server.py

# 或者使用自定义配置
python server/server.py --host 0.0.0.0 --port 8080 --static-dir src/main/webapp
```

4. **访问应用:**
- 打开浏览器访问 `http://localhost:8080` (或您配置的地址)
- 开始使用draw.io进行图表编辑

5. **验证安装:**
- 测试图表加载和保存功能
- 验证服务器文件列表功能 (访问 `/list` 端点)
- 运行Python脚本验证工具正常工作

## 使用示例

### 服务器部署示例

#### 本地开发环境
```bash
# 启动开发服务器
python server/server.py

# 访问 http://localhost:8080
# 创建图表并保存到服务器
```

#### 生产环境部署
```bash
# 监听所有接口，自定义端口
python server/server.py --host 0.0.0.0 --port 80 --static-dir /var/www/drawio

# 使用systemd管理服务 (可选)
sudo systemctl start drawio-server
```

#### 服务器API使用示例
```bash
# 获取服务器状态
curl http://localhost:8080/health

# 列出保存的文件
curl http://localhost:8080/list

# 打开特定文件
curl http://localhost:8080/open/my-diagram_20231201_143022.drawio
```

### 完整工作流程示例

```bash
# 1. 启动服务器
python server/server.py --port 8080

# 2. 提取现有图表的网表数据
python3 scripts/extract_netlist.py demo_files -o extracted_data

# 3. 检测网络中的环路
python3 scripts/detect_cycles.py extracted_data -o cycle_analysis

# 4. 在Web界面中访问 http://localhost:8080
# 5. 使用draw.io加载和编辑图表，保存到服务器
```

在JavaScript中:
```javascript
// 加载图表
window.ohtoai.loadGraphXML('demo/network.drawio.xml')
  .then(() => {
    // 设置高亮显示告警组件
    const graph = window.sb.editorUi.editor.graph;
    const manager = new StripedOverlayManager(graph);
    
    manager.addConditionalHighlight('alarms', 
      cell => cell.value?.getAttribute('alarm') === '1',
      ['#ff0000', '#ffff00']
    );
    
    manager.refresh();
  });

// 保存到服务器
window.ohtoai.saveToServer('updated-network.drawio');
```

## 开发指南

### 项目结构
```
drawio/
├── src/main/webapp/js/mod.js     # JavaScript API实现
├── server/                      # HTTP服务器
│   ├── server.py                # 主服务器文件
│   └── saved_files/             # 服务器保存的图表文件
├── scripts/                      # Python工具脚本
│   ├── terminal_data_model.py   # 端子数据模型与接线图生成
│   ├── extract_netlist.py       # 网表提取
│   ├── detect_cycles.py         # 环路检测
│   ├── gen_graph.py             # 图表生成
│   └── random_topo.py           # 随机拓扑
├── demo/                        # 示例文件
└── README.md                    # 本文档
```

### API扩展指南

要添加新的JavaScript API:

1. 在`mod.js`中实现功能函数
2. 添加JSDoc文档注释
3. 在`window.ohtoai`对象中注册API
4. 更新本README文档

### 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

### 许可证

本项目基于原始Draw.io项目构建，遵循相应的开源许可证。详见 [LICENSE](LICENSE) 文件。

---

## 快速参考

### JavaScript API 快速索引

| API函数 | 功能 | 返回值 |
|---------|------|--------|
| `loadGraphXML(url, readonly?)` | 加载图表文件 | `Promise<LocalFile>` |
| `enableEditing()` | 启用编辑模式 | `boolean` |
| `disableEditing()` | 禁用编辑模式 | `boolean` |
| `isEditingEnabled()` | 检查编辑状态 | `boolean` |
| `saveToServer(filename, success?, error?)` | 保存到服务器 | `void` |
| `loadLibraryFromServer(path, success?, error?)` | 加载形状库 | `void` |

### Python脚本快速索引

| 脚本 | 功能 | 主要参数 |
|------|------|----------|
| `server/server.py` | HTTP服务器 | `--host`, `--port`, `--static-dir`, `--save-dir` |
| `terminal_data_model.py` | 端子数据模型与接线图 | Excel文件路径 |
| `extract_netlist.py` | 提取网表数据 | `input_dir`, `-o output` |
| `detect_cycles.py` | 检测网络环路 | `input_dir`, `-o output` |
| `gen_graph.py` | 生成图表XML | 无参数 |
| `random_topo.py` | 生成随机拓扑 | 无参数 |

### 全局对象

所有API都通过 `window.ohtoai` 对象提供：
- `window.ohtoai.loadGraphXML()`
- `window.ohtoai.stripedOverlayManager` (自动创建的高亮管理器实例)
- 其他API函数...

### 典型工作流程

1. **服务器启动和基本使用:**
   ```bash
   # 启动服务器
   python server/server.py --host 0.0.0.0 --port 8080
   
   # 访问 http://localhost:8080 使用draw.io
   # 保存图表到服务器，从服务器打开图表
   ```

2. **网表分析流程:**
   ```bash
   python3 scripts/extract_netlist.py demo_files -o netlist_data
   python3 scripts/detect_cycles.py netlist_data -o cycles
   ```

3. **图表操作流程:**
   ```javascript
   // 加载 -> 设置高亮 -> 编辑 -> 保存
   window.ohtoai.loadGraphXML('diagram.xml')
     .then(() => window.ohtoai.enableEditing())
     .then(() => window.ohtoai.saveToServer('updated.xml'));
   ```
