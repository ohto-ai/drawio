# 端子排信息系统重构总结

## 概述

本次重构完全重新设计了 `scripts/terminal_block_info.py` 的数据模型，以更好地表示电气机柜系统的结构和连接关系。

## 主要变更

### 1. 新的数据模型

#### 核心类

**Cabinet (机柜)**
- 属性：编号、端子排字典、装置字典、元件字典、说明
- 功能：作为端子排、装置和元件的容器

**TerminalBlock (端子排)**
- 属性：名称、端子列表（纵向排列）、说明
- 功能：管理纵向排列的端子组合
- 完整引用格式：`机柜/端子排:端子号`

**Terminal (端子)**
- 属性：名称、回路号（可选）、电缆编号（可选）
- 功能：表示基本的连接点

**Device (装置)**
- 属性：名称、端子列表、行数、列数、说明
- 功能：表示带有规则布局端子的容器（矩形阵列，可有缺失位置）
- 完整引用格式：`机柜/装置端子号`

**DeviceTerminal (装置端子)**
- 属性：名称、行位置、列位置
- 功能：表示装置内的端子及其位置

**Component (元件)**
- 属性：名称、类型、端子列表、说明、内部连接
- 类型：开关、压板、继电器、其他
- 功能：表示具有固定形状的电子器件
- 完整引用格式：`机柜/元件:端子号`

**ComponentTerminal (元件端子)**
- 属性：名称、位置索引
- 功能：表示元件上的固定端子

**Connection (连接)**
- 属性：源端子引用、目标端子引用、连接类型、回路号、电缆编号、元件名称、说明
- 类型：直连、内部连线、回路、经过元件
- 功能：描述两个端子之间的连接关系

**CabinetSystem (机柜系统)**
- 属性：机柜字典、连接列表、回路字典
- 功能：管理多个机柜及其之间的连接关系
- 方法：
  - 添加/获取机柜
  - 添加连接
  - 解析端子引用
  - 获取连接的端子
  - 验证连接有效性

### 2. 连接规则

#### 端子排端子
1. 可以直接互联本机柜内的其他端子
2. 可以通过内部连线连接到所在机柜内的装置或元件的端子
3. 可以通过回路连接到其他机柜的端子（**必须同时有回路号和电缆编号**）

#### 装置端子
1. 可以直连其他装置端子
2. 可以连接到端子排端子（作为出口）
3. 可以连接到元件端子
4. **不能直接通过回路号/电缆号接出**（必须使用端子排端子作为出口）

#### 元件端子
1. 根据元件类型有固定的内部连接关系
2. 可以连接到端子排端子
3. 可以连接到装置端子

#### 回路连接
- **必须同时具有回路号和电缆编号才能代表互联**
- 仅回路号或电缆编号相同不能代表互联

### 3. 向后兼容

#### LegacyConverter 类
- 将旧的 `TerminalInfo` 数据转换为新的 `CabinetSystem` 模型
- 自动解析端子引用并创建连接关系
- 保留所有原有功能

#### ConnectionGraph 增强
- 新增 `build_from_cabinet_system()` 方法支持新模型
- 保留 `build_from_terminals()` 方法支持旧模型
- 新增 `export_system_to_drawio()` 方法用于批量导出

### 4. 新增功能

#### 验证功能
- 连接有效性验证
- 端子引用检查
- 回路连接完整性检查

#### 查询功能
- 根据端子引用获取端子对象
- 获取连接的所有端子（递归查找）
- 根据回路查询连接
- 解析和验证端子引用格式

#### 导出功能
- 支持按机柜分离导出
- 支持导出所有组件
- 改进的布局算法

## 文件结构

```
scripts/
├── terminal_block_info.py          # 主模块（重构后）
├── test_new_model.py               # 基础测试
├── example_cabinet_system.py       # 简单示例
└── example_complex_system.py       # 复杂系统示例

docs/
└── TERMINAL_BLOCK_MODEL.md         # 完整文档
```

## 测试结果

### 基础测试 (test_new_model.py)
- ✓ 端子和端子排测试通过
- ✓ 装置测试通过
- ✓ 元件测试通过
- ✓ 机柜测试通过
- ✓ 完整系统测试通过

### 示例运行
- ✓ 简单系统示例运行成功
- ✓ 复杂系统示例运行成功
- ✓ 包含3个机柜，23个连接，验证通过

### 安全检查
- ✓ CodeQL 分析：0 个安全问题

## 使用示例

### 创建系统

```python
from terminal_block_info import *

# 创建系统
system = CabinetSystem()

# 创建机柜
cabinet = Cabinet(number="CAB001", description="主控制柜")

# 添加端子排
tb = TerminalBlock(name="TB1", description="电源端子排")
tb.add_terminal(Terminal(name="L1", circuit_number="PWR_L1", cable_number="CABLE001"))
cabinet.add_terminal_block(tb)

# 添加装置
device = Device(name="PLC_001", description="PLC模块")
device.add_terminal(DeviceTerminal(name="DI1", row=0, col=0))
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
    connection_type=ConnectionType.INTERNAL_WIRE
)
system.add_connection(connection)

# 验证
errors = system.validate_connections()
if not errors:
    print("验证通过！")
```

### 导出图纸

```python
# 构建连接图
graph = ConnectionGraph()
graph.build_from_cabinet_system(system)

# 导出所有组件
graph.export_system_to_drawio(Path("output"))
```

### 从旧格式转换

```python
# 读取旧格式
reader = TerminalBlockReader()
terminal_infos = reader.read_from_excel("data.xlsx")

# 转换为新模型
converter = LegacyConverter()
system = converter.convert_to_cabinet_system(terminal_infos)

# 使用新模型
graph = ConnectionGraph()
graph.build_from_cabinet_system(system)
```

## 优点

1. **清晰的数据模型**：各个概念（机柜、端子排、装置、元件）都有明确的类表示
2. **类型安全**：使用枚举类型表示连接类型和元件类型
3. **灵活的布局**：装置支持矩形阵列布局，可以有缺失位置
4. **强大的验证**：内置连接有效性验证和回路完整性检查
5. **向后兼容**：保留旧格式支持，通过转换器无缝过渡
6. **完整文档**：包含详细的API文档和使用示例
7. **易于扩展**：清晰的类结构便于后续功能扩展

## 后续改进

1. 增强的 draw.io 布局算法
2. 自动布线算法优化
3. 连接路径查找和高亮
4. 导出为其他格式（PDF、SVG）
5. 图形化编辑界面
6. 更多的元件类型支持
7. 批量导入/导出功能

## 依赖

- Python 3.6+
- pandas（用于Excel读取）
- openpyxl（用于Excel文件支持）

## 结论

本次重构成功实现了需求中的所有功能点：
- ✅ 多机柜管理及连接关系
- ✅ 端子排的纵向排列结构
- ✅ 装置的矩形阵列布局（支持缺失位置）
- ✅ 元件的固定端子位置和内部连接
- ✅ 回路的完整性要求（回路号+电缆编号）
- ✅ 清晰的端子引用格式
- ✅ 完整的连接规则实现
- ✅ Draw.io图纸生成和布局

所有测试通过，无安全问题，代码质量良好，文档完整。
