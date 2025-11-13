# 端子排信息系统 - 数据模型文档

## 概述

本文档描述了重构后的端子排信息系统的数据模型。该系统用于管理电气机柜系统中的端子排、装置、元件及其连接关系，并能生成 draw.io 图纸。

## 核心概念

### 1. 机柜 (Cabinet)

机柜是包含端子排、装置和元件的物理容器。

**属性：**
- `number`: 机柜编号（唯一标识）
- `terminal_blocks`: 端子排字典
- `devices`: 装置字典
- `components`: 元件字典
- `description`: 机柜说明

**示例：**
```python
cabinet = Cabinet(
    number="CAB001",
    description="主控制柜"
)
```

### 2. 端子排 (TerminalBlock)

端子排是纵向排列的端子组合，带有名称属性。不同机柜的端子排可能重名。

**属性：**
- `name`: 端子排名称
- `terminals`: 端子列表（纵向排列）
- `description`: 端子排说明

**方法：**
- `add_terminal(terminal)`: 添加端子
- `get_terminal(name)`: 根据名称获取端子

**完整引用格式：** `机柜/端子排:端子号`

**示例：**
```python
terminal_block = TerminalBlock(
    name="TB1",
    description="电源端子排"
)
terminal_block.add_terminal(Terminal(name="L1"))
terminal_block.add_terminal(Terminal(name="L2"))

# 完整引用: CAB001/TB1:L1
```

### 3. 端子 (Terminal)

端子是连接点，具有名称属性。

**属性：**
- `name`: 端子名称
- `circuit_number`: 回路号（可选）
- `cable_number`: 电缆编号（可选）

**示例：**
```python
terminal = Terminal(
    name="1",
    circuit_number="C001",
    cable_number="CAB001"
)
```

### 4. 装置 (Device)

装置是带有规则布局端子的容器，一般是矩形阵列，但可能会缺少一些位置的端子。

**属性：**
- `name`: 装置名称
- `terminals`: 装置端子列表
- `rows`: 行数（自动计算）
- `cols`: 列数（自动计算）
- `description`: 装置说明

**方法：**
- `add_terminal(terminal)`: 添加端子（自动更新行列数）
- `get_terminal(name)`: 根据名称获取端子
- `get_terminal_at(row, col)`: 获取指定位置的端子

**完整引用格式：** `机柜/装置端子号`

**示例：**
```python
device = Device(
    name="PLC_001",
    description="PLC模块"
)
# 2行3列的矩形阵列，但缺少(1,2)位置
device.add_terminal(DeviceTerminal(name="D1", row=0, col=0))
device.add_terminal(DeviceTerminal(name="D2", row=0, col=1))
device.add_terminal(DeviceTerminal(name="D3", row=0, col=2))
device.add_terminal(DeviceTerminal(name="D4", row=1, col=0))
device.add_terminal(DeviceTerminal(name="D5", row=1, col=1))
# (1, 2) 位置缺失

# 完整引用: CAB001/PLC_001/D1
```

### 5. 装置端子 (DeviceTerminal)

装置内的端子，带有位置信息。

**属性：**
- `name`: 端子名称（机柜内独立名称）
- `row`: 行位置
- `col`: 列位置

### 6. 元件 (Component)

元件是具有固定形状的电子器件（如开关、压板），具有固定的端子位置。

**属性：**
- `name`: 元件名称
- `component_type`: 元件类型（枚举）
- `terminals`: 元件端子列表
- `description`: 元件说明
- `internal_connections`: 元件内部连接关系列表

**元件类型：**
- `SWITCH`: 开关
- `PRESSURE_PLATE`: 压板
- `RELAY`: 继电器
- `OTHER`: 其他

**方法：**
- `add_terminal(terminal)`: 添加端子
- `get_terminal(name)`: 根据名称获取端子
- `add_internal_connection(terminal1, terminal2)`: 添加内部连接

**完整引用格式：** `机柜/元件:端子号`

**示例：**
```python
switch = Component(
    name="QF1",
    component_type=ComponentType.SWITCH,
    description="主电源断路器"
)
switch.add_terminal(ComponentTerminal(name="1", position=0))
switch.add_terminal(ComponentTerminal(name="2", position=1))
switch.add_internal_connection("1", "2")

# 完整引用: CAB001/QF1:1
```

### 7. 连接 (Connection)

连接描述两个端子之间的连接关系。

**属性：**
- `from_ref`: 源端子引用
- `to_ref`: 目标端子引用
- `connection_type`: 连接类型（枚举）
- `circuit_number`: 回路号（用于回路连接）
- `cable_number`: 电缆编号（用于回路连接）
- `component_name`: 元件名称（用于经过元件的连接）
- `description`: 连接说明

**连接类型：**
- `DIRECT`: 直连 - 端子直接互联
- `INTERNAL_WIRE`: 内部连线 - 机柜内部连线
- `CIRCUIT`: 回路 - 通过回路号连接
- `THROUGH_COMPONENT`: 经过元件 - 通过元件连接

**示例：**
```python
# 直连
connection1 = Connection(
    from_ref="CAB001/TB1:1",
    to_ref="CAB001/TB1:2",
    connection_type=ConnectionType.DIRECT
)

# 回路连接
connection2 = Connection(
    from_ref="CAB001/TB1:1",
    to_ref="CAB002/TB2:1",
    connection_type=ConnectionType.CIRCUIT,
    circuit_number="C001",
    cable_number="CABLE001"
)
```

### 8. 机柜系统 (CabinetSystem)

机柜系统管理多个机柜及其之间的连接关系。

**属性：**
- `cabinets`: 机柜字典
- `connections`: 连接列表
- `circuits`: 回路字典（回路号 -> 端子引用列表）

**方法：**
- `add_cabinet(cabinet)`: 添加机柜
- `get_cabinet(number)`: 获取机柜
- `add_connection(connection)`: 添加连接
- `parse_terminal_ref(ref)`: 解析端子引用
- `get_terminal_by_ref(ref)`: 根据引用获取端子对象
- `get_connected_terminals(ref)`: 获取连接的所有端子
- `get_connections_by_circuit(circuit_number, cable_number)`: 获取回路的连接
- `validate_connections()`: 验证连接有效性

**示例：**
```python
system = CabinetSystem()

# 添加机柜
cabinet1 = Cabinet(number="CAB001")
system.add_cabinet(cabinet1)

# 添加连接
connection = Connection(
    from_ref="CAB001/TB1:1",
    to_ref="CAB001/TB1:2",
    connection_type=ConnectionType.DIRECT
)
system.add_connection(connection)

# 验证连接
errors = system.validate_connections()
if errors:
    print("连接错误:", errors)
```

## 连接规则

### 端子排端子的连接规则

端子排内的端子可以：
1. **直接互联本机柜内的其他端子**
   - 同一端子排内的端子可以直连
   - 不同端子排的端子可以直连
   
2. **通过内部连线连接到所在机柜内的装置或元件的端子**
   - 可以连接到装置端子
   - 可以连接到元件端子
   
3. **通过回路连接到其他机柜的端子**
   - **重要**: 必须同时有回路号和电缆编号
   - 仅回路号或仅电缆编号相同不能代表互联

### 装置端子的连接规则

装置内的端子可以：
1. **直连其他装置端子**
2. **连接到端子排端子（作为出口）**
3. **连接到元件端子**
4. **不能直接通过回路号/电缆号接出**
   - 必须使用端子排端子作为出口

### 元件端子的连接规则

元件内的端子：
1. **根据元件类型有固定的内部连接关系**
   - 例如：开关的两个端子内部相连
2. **可以连接到端子排端子**
3. **可以连接到装置端子**

### 回路连接规则

回路具有以下特征：
1. **必须同时具有回路号和电缆编号才能代表互联**
2. **多个端子具有相同的回路号和电缆编号，则代表它们互联**
3. **仅回路号或电缆编号相同不能代表互联**
   - 原因：它们可能只是使用了同一个回路号，或者借助同一个电缆接线

## 端子引用格式

### 格式说明

1. **端子排端子**: `机柜/端子排:端子号`
   - 示例: `CAB001/TB_POWER:L1`
   - 机柜: `CAB001`
   - 端子排: `TB_POWER`
   - 端子号: `L1`

2. **装置端子**: `机柜/装置端子号`
   - 示例: `CAB001/PLC_001/DI1`
   - 机柜: `CAB001`
   - 装置: `PLC_001`
   - 端子号: `DI1`

3. **元件端子**: `机柜/元件:端子号`
   - 示例: `CAB001/QF1:1`
   - 机柜: `CAB001`
   - 元件: `QF1`
   - 端子号: `1`

## 向后兼容

为了保持向后兼容，系统保留了原有的 `TerminalInfo` 类和相关功能。

### LegacyConverter

`LegacyConverter` 类提供了将旧的 `TerminalInfo` 数据转换为新模型的功能。

**示例：**
```python
# 读取旧格式数据
reader = TerminalBlockReader()
terminal_infos = reader.read_from_excel("data.xlsx")

# 转换为新模型
converter = LegacyConverter()
system = converter.convert_to_cabinet_system(terminal_infos)

# 使用新模型
for cabinet in system.cabinets.values():
    print(f"机柜: {cabinet.number}")
```

### ConnectionGraph

`ConnectionGraph` 类已更新以支持新模型，同时保持与旧模型的兼容性。

**新方法：**
```python
graph = ConnectionGraph()

# 从新模型构建
graph.build_from_cabinet_system(system)

# 从旧模型构建（仍然支持）
graph.build_from_terminals(terminal_infos)
```

## 示例代码

完整的示例代码请参见：
- `scripts/test_new_model.py` - 基本数据模型测试
- `scripts/example_cabinet_system.py` - 完整系统示例

### 创建简单系统示例

```python
from terminal_block_info import *

# 创建机柜系统
system = CabinetSystem()

# 创建机柜
cabinet = Cabinet(number="CAB001", description="主控制柜")

# 添加端子排
tb = TerminalBlock(name="TB1", description="电源端子排")
tb.add_terminal(Terminal(name="L1", circuit_number="PWR_L1", cable_number="CABLE001"))
tb.add_terminal(Terminal(name="L2", circuit_number="PWR_L2", cable_number="CABLE001"))
cabinet.add_terminal_block(tb)

# 添加装置
device = Device(name="PLC_001", description="PLC模块")
for i in range(8):
    device.add_terminal(DeviceTerminal(name=f"DI{i+1}", row=i//4, col=i%4))
cabinet.add_device(device)

# 添加元件
switch = Component(name="QF1", component_type=ComponentType.SWITCH)
switch.add_terminal(ComponentTerminal(name="1", position=0))
switch.add_terminal(ComponentTerminal(name="2", position=1))
switch.add_internal_connection("1", "2")
cabinet.add_component(switch)

# 添加到系统
system.add_cabinet(cabinet)

# 添加连接
connection = Connection(
    from_ref="CAB001/TB1:L1",
    to_ref="CAB001/QF1:1",
    connection_type=ConnectionType.INTERNAL_WIRE,
    description="电源线"
)
system.add_connection(connection)

# 验证
errors = system.validate_connections()
if not errors:
    print("系统验证通过！")

# 生成图纸
graph = ConnectionGraph()
graph.build_from_cabinet_system(system)
# ... 导出 drawio
```

## 数据验证

系统提供了连接验证功能：

```python
errors = system.validate_connections()
for error in errors:
    print(f"错误: {error}")
```

验证检查包括：
1. 源端子是否存在
2. 目标端子是否存在
3. 回路连接是否同时有回路号和电缆编号

## 未来增强

计划中的功能：
1. 增强的 draw.io 布局算法，更好地展示装置和元件
2. 自动布线算法优化
3. 连接路径查找和高亮
4. 导出为其他格式（如PDF、SVG）
5. 图形化编辑界面

## 贡献

欢迎贡献代码和提出建议！请遵循现有的代码风格和文档规范。
