# 互联类型功能说明 (Connection Types Feature)

## 概述

terminal_data_model.py 现在支持在后端装置互联中指定连接类型。当指定连接类型（如"刀开关"）时，系统会在两个端子之间自动插入一个中间节点来表示该连接元件。

## 功能特性

- **默认行为**：如果不指定互联类型或互联类型为空，保持原有的直接连线行为
- **中间节点渲染**：当指定的互联类型在 `COMPONENT_GRAPHICS` 中定义时，会创建一个无名的中间节点
- **智能定位** (v1.1)：中间节点自动放置在两个端子的中点位置，提供更清晰的布局
- **透明连线** (v1.1)：特殊的"空接"类型使用透明连线，表示电气连接但在图中不显示
- **图形复用**：使用 `COMPONENT_GRAPHICS` 中预定义的图形样式来渲染中间节点
- **边拆分**：原本的单条边会被拆分为两条边：起点 → 中间节点 → 终点

## Excel 数据格式

在后端装置互联数据表中，添加一个新列"互联类型"：

```
设备编号       互联起点    互联终点    互联类型
1ABA03GG003   61LHn      1DK:1       
1ABA03GG003   1DK:1      61LHNa      刀开关
1ABA03GG003   42LHa      42LHb       
```

### 列说明

| 列名 | 必填 | 说明 |
|------|------|------|
| 设备编号 | 是 | 机柜/设备的唯一标识 |
| 互联起点 | 是 | 连接的起始端子 |
| 互联终点 | 是 | 连接的目标端子 |
| 互联类型 | 否 | 连接类型名称，必须在 `COMPONENT_GRAPHICS` 中定义 |

## 支持的连接类型

当前 `COMPONENT_GRAPHICS` 中预定义的连接类型包括：

- **闭合开关**：开关闭合状态
- **刀开关**：开关断开状态
- **双刀开关**：双刀双掷开关
- **压板**：压板元件
- **LED**：LED指示灯
- **空接** (v1.1)：特殊类型，使用透明连线表示电气连接但不显示线条

可以通过修改 `COMPONENT_GRAPHICS` 字典来添加更多类型。

## 添加自定义连接类型

在 `terminal_data_model.py` 文件开头的 `COMPONENT_GRAPHICS` 字典中添加新的类型定义：

```python
COMPONENT_GRAPHICS: Dict[str, Dict[str, object]] = {
    # 现有类型...
    
    # 添加新类型
    "继电器": {
        "style": "html=1;shape=mxgraph.electrical.electro-mechanical.relay;",
        "width": 60,
        "height": 40,
        "value": ""
    },
}
```

### 图形定义参数

| 参数 | 类型 | 说明 |
|------|------|------|
| style | string | draw.io 的图形样式定义 |
| width | int | 图形宽度（像素） |
| height | int | 图形高度（像素） |
| value | string | 图形上显示的文本（通常为空） |

## 工作原理

### 1. 数据加载

```python
# 在 _process_backend_connections_dataframe 中
connection_type = TerminalDataModel.safe_str(row.get("互联类型", ""))
if not connection_type:
    connection_type = None

backend_connection = BackendConnection(
    from_terminal=from_terminal_ref,
    to_terminal=to_terminal_ref,
    connection_type=connection_type
)
```

### 2. 连接图构建

```python
# 在 build_connection_graph 中
for bc in cabinet.backend_connections:
    graph.add_edge(bc.from_terminal, bc.to_terminal, 
                  "backend_connection", 
                  connection_type=bc.connection_type)
```

### 3. XML 渲染

```python
# 在 to_drawio_xml 中
conn_type = self.connection_types.get(key)

if conn_type and conn_type in COMPONENT_GRAPHICS:
    # 创建中间节点
    gfx = COMPONENT_GRAPHICS[conn_type]
    intermediate_id = gen_id()
    
    # 创建中间节点元素
    comp_cell = ET.SubElement(root, "mxCell", 
                             id=intermediate_id, 
                             value=gfx.get("value", ""),
                             style=gfx.get("style", ""), 
                             vertex="1", 
                             parent="1")
    
    # 创建两条边
    # 边1: source -> intermediate
    # 边2: intermediate -> target
```

## 使用示例

### 示例 1：简单的刀开关连接

Excel 数据：
```
设备编号       互联起点    互联终点    互联类型
1ABA03GG003   Terminal1  Terminal2   刀开关
```

生成的连接图：
```
Terminal1 ----[刀开关]---- Terminal2
```

### 示例 2：混合连接

Excel 数据：
```
设备编号       互联起点    互联终点    互联类型
1ABA03GG003   T1         T2          刀开关
1ABA03GG003   T2         T3          
1ABA03GG003   T3         T4          LED
```

生成的连接图：
```
T1 ----[刀开关]---- T2 -------- T3 ----[LED]---- T4
```

## 测试

运行测试脚本验证功能：

```bash
cd scripts
python3 test_connection_types.py
```

测试脚本会：
1. 创建包含互联类型的测试数据
2. 加载数据并构建连接图
3. 导出为 draw.io XML 文件
4. 验证生成的 XML 包含中间节点

## 注意事项

1. **类型名称必须精确匹配**：互联类型的名称必须与 `COMPONENT_GRAPHICS` 中的键完全一致
2. **未定义类型会被忽略**：如果指定的互联类型在 `COMPONENT_GRAPHICS` 中不存在，将回退为直接连线
3. **节点布局**：中间节点使用相对定位，draw.io 会自动调整其位置
4. **无名节点**：中间节点不会显示名称，仅显示图形元素

## 扩展性

该功能设计具有良好的扩展性：

- 可以通过修改 `COMPONENT_GRAPHICS` 添加任意数量的新连接类型
- 支持任何 draw.io 兼容的图形样式
- 不影响现有的直接连线行为（向后兼容）
- 可以在同一数据集中混合使用不同的连接类型

## 技术细节

### 数据结构

```python
@dataclass
class BackendConnection:
    from_terminal: TerminalRef
    to_terminal: TerminalRef
    connection_type: Optional[str] = None  # 新增字段

@dataclass
class ConnectionGraph:
    # ... 其他字段 ...
    connection_types: Dict[frozenset, Optional[str]] = field(default_factory=dict)  # 新增字段
```

### 边拆分逻辑

原始边：
```
A ---------> B
```

带连接类型的边：
```
A -----> [中间节点] -----> B
```

在 XML 中表示为：
```xml
<!-- 中间节点 -->
<mxCell id="N" value="" style="..." vertex="1" parent="1">
    <mxGeometry x="0" y="0" width="75" height="20" as="geometry" relative="1"/>
</mxCell>

<!-- 边1: A -> N -->
<mxCell id="E1" edge="1" parent="1" source="A" target="N">
    <mxGeometry relative="1" as="geometry"/>
</mxCell>

<!-- 边2: N -> B -->
<mxCell id="E2" edge="1" parent="1" source="N" target="B">
    <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

## 版本历史

- **v1.1** (2025-01-08): 优化更新
  - ✨ 新增"空接"类型：使用透明连线表示电气连接但不显示线条
  - 🎯 智能定位：中间节点自动放置在两个端子的中点位置
  - 📐 改进布局：基于实际端子位置计算组件摆放位置
  
- **v1.0** (2025-01-08): 初始实现
  - 添加互联类型支持
  - 实现中间节点自动插入
  - 支持 COMPONENT_GRAPHICS 中定义的所有类型

## 新功能详解 (v1.1)

### 1. "空接"类型

"空接"类型用于表示两个端子之间存在电气连接，但在图纸上不显示连线。这在以下场景中很有用：
- 表示内部跳线但不希望在图中显示
- 简化复杂图纸，隐藏某些连接
- 表示逻辑连接而非物理连接

**使用示例：**
```
设备编号    互联起点    互联终点    互联类型
CAB001     T1         T2         空接
```

**生成效果：**
- 端子T1和T2之间有透明边（strokeColor=none）
- 在draw.io中不可见，但保持连接关系
- 不创建中间节点

### 2. 智能定位

中间节点现在会自动计算并放置在两个端子的中点位置，而不是使用相对定位让draw.io自动布局。

**优势：**
- ✅ 更清晰的布局：组件准确位于连接中点
- ✅ 更少的手动调整：生成的图纸即可直接使用
- ✅ 一致性：所有中间节点按统一规则放置

**技术实现：**
```python
# 计算中点位置
mid_x = (pos_a[0] + pos_b[0]) // 2
mid_y = (pos_a[1] + pos_b[1]) // 2

# 调整使组件中心对齐中点
comp_x = mid_x - comp_width // 2
comp_y = mid_y - comp_height // 2
```

### 3. 使用建议

**何时使用"空接"：**
- ✅ 端子之间需要逻辑连接但不希望显示连线
- ✅ 简化复杂图纸，去除视觉干扰
- ✅ 表示可选连接或条件连接

**何时使用普通连接类型：**
- ✅ 需要显示具体的连接元件（开关、LED等）
- ✅ 需要在图中明确标识连接方式
- ✅ 常规的电气连接表示

**布局优化建议：**
- 对于密集的端子组，考虑使用矩阵布局增加间距
- 合理安排端子顺序，使中间节点不会重叠
- 必要时可以在draw.io中手动微调位置
