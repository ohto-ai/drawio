# Draw.io Enhanced Edition

一个增强版的Draw.io图表编辑器，支持网络拓扑分析、智能高亮管理和服务器端集成功能。

## 目录

- [功能特性](#功能特性)
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
- **服务器集成**: 支持保存文件到服务器而非客户端下载
- **网络拓扑分析**: 提取、分析和可视化网络连接关系

### 增强特性
- 条纹覆盖高亮管理器 (StripedOverlayManager)
- 网络环路检测和可视化
- 网表提取和CSV导出
- 随机拓扑生成工具

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

本项目包含四个强大的Python工具脚本，用于网络拓扑分析和可视化。

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
- Java Web服务器 (可选，用于服务器保存功能)

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

3. **启动Web服务器:**
```bash
# 使用内置服务器或配置Apache/Nginx
# 确保src/main/webapp/为Web根目录
```

4. **验证安装:**
- 在浏览器中访问编辑器
- 测试图表加载和保存功能
- 运行Python脚本验证工具正常工作

## 使用示例

### 完整工作流程示例

```bash
# 1. 提取现有图表的网表数据
python3 scripts/extract_netlist.py demo_files -o extracted_data

# 2. 检测网络中的环路
python3 scripts/detect_cycles.py extracted_data -o cycle_analysis

# 3. 在Web界面中加载和编辑图表
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
├── scripts/                      # Python工具脚本
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

1. **网表分析流程:**
   ```bash
   python3 scripts/extract_netlist.py demo_files -o netlist_data
   python3 scripts/detect_cycles.py netlist_data -o cycles
   ```

2. **图表操作流程:**
   ```javascript
   // 加载 -> 设置高亮 -> 编辑 -> 保存
   window.ohtoai.loadGraphXML('diagram.xml')
     .then(() => window.ohtoai.enableEditing())
     .then(() => window.ohtoai.saveToServer('updated.xml'));
   ```
