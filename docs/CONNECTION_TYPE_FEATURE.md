# 互联类型功能说明 (Connection Type Feature)

## 概述 (Overview)

此增强功能允许在后端装置互联数据中指定连接类型（互联类型），从而在绘制时自动插入中间组件节点（如刀开关、压板等）。

This enhancement allows specifying connection types in backend connections data, enabling automatic insertion of intermediate component nodes (such as knife switches, compression plates, etc.) during rendering.

## 使用方法 (Usage)

### Excel 数据格式 (Excel Data Format)

在后端互联数据表中添加"互联类型"列：

```
设备编号        互联起点    互联终点    互联类型
1ABA03GG003    61LHa      61LHb       
1ABA03GG003    61LHb      61LHc       刀开关
1ABA03GG003    61LHc      1DK:1       压板
1ABA03GG003    1DK:1      61LHn       
1ABA03GG003    2DK:1      42LH:1      双刀开关
```

### 互联类型说明 (Connection Types)

- **空值/不填**: 默认行为，直接连线
- **刀开关**: 插入刀开关图形元件
- **压板**: 插入压板图形元件
- **双刀开关**: 插入双刀开关图形元件
- **闭合开关**: 插入闭合开关图形元件
- **LED**: 插入LED图形元件

可使用 `COMPONENT_GRAPHICS` 字典中定义的任何类型名称。

## 技术实现 (Technical Implementation)

### 1. 数据结构变更

`BackendConnection` 类增加了 `connection_type` 字段：

```python
@dataclass
class BackendConnection:
    from_terminal: TerminalRef
    to_terminal: TerminalRef
    connection_type: Optional[str] = None  # 新增字段
```

### 2. 数据读取

`_process_backend_connections_dataframe` 方法从Excel读取"互联类型"列：

```python
connection_type = TerminalDataModel.safe_str(row.get("互联类型", ""))
if not connection_type:
    connection_type = None
```

### 3. 连接图构建

在 `build_connection_graph` 方法中，当检测到非空的 `connection_type` 时：

1. 创建一个中间组件节点（使用唯一ID: `_CONN_{类型}_{id}`）
2. 注册为 `BackendComponentInfo`，类型为指定的互联类型
3. 将原始连接拆分为两条边：
   - `from_terminal -> intermediate_component`
   - `intermediate_component -> to_terminal`

```python
if bc.connection_type:
    intermediate_component_id = f"_CONN_{bc.connection_type}_{id(bc)}"
    intermediate_ref = TerminalRef(
        cabinet_id=cabinet.id,
        component_id=intermediate_component_id,
        terminal_name="",
        terminal_type=TerminalType.BACKEND_COMPONENT
    )
    # ... 注册组件信息 ...
    graph.add_edge(bc.from_terminal, intermediate_ref, "backend_connection_with_component")
    graph.add_edge(intermediate_ref, bc.to_terminal, "backend_connection_with_component")
else:
    graph.add_edge(bc.from_terminal, bc.to_terminal, "backend_connection")
```

### 4. 渲染

中间组件节点会在 `to_drawio_xml` 方法中使用 `COMPONENT_GRAPHICS` 字典中定义的图形样式进行渲染。

## 示例 (Examples)

### 示例 1: 简单刀开关连接

**输入数据:**
```
设备编号: 1ABA03GG003
互联起点: A
互联终点: B
互联类型: 刀开关
```

**结果:**
- 创建中间节点: `1ABA03GG003/@COMPONENT:_CONN_刀开关_xxx:`
- 生成两条边: `A -> 中间节点`, `中间节点 -> B`
- 中间节点使用刀开关图形渲染

### 示例 2: 混合连接

**输入数据:**
```
设备编号        互联起点    互联终点    互联类型
1ABA03GG003    A          B           刀开关
1ABA03GG003    B          C           
1ABA03GG003    C          D           压板
```

**结果:**
- A -> 刀开关中间节点 -> B
- B -> C (直接连接)
- C -> 压板中间节点 -> D

## 向后兼容性 (Backward Compatibility)

此功能完全向后兼容：

1. ✅ 旧的Excel文件（没有"互联类型"列）仍然正常工作
2. ✅ "互联类型"列为空或空白时，使用默认的直接连线行为
3. ✅ 现有的代码逻辑和测试不受影响

## 扩展新类型 (Adding New Types)

要添加新的互联类型，在 `COMPONENT_GRAPHICS` 字典中定义即可：

```python
COMPONENT_GRAPHICS: Dict[str, Dict[str, object]] = {
    "你的新类型": {
        "style": "html=1;shape=...",
        "width": 75,
        "height": 20,
        "value": ""
    },
    # ...
}
```

然后在Excel的"互联类型"列中使用"你的新类型"即可。

## 测试 (Testing)

运行测试脚本验证功能：

```bash
python /tmp/test_connection_type.py
python /tmp/test_integration.py
```

所有测试均已通过：
- ✅ 基本连接类型读取
- ✅ 中间组件创建
- ✅ Drawio导出
- ✅ 向后兼容性
