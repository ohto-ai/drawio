# 端子排信息系统脚本

本目录包含用于管理电气机柜系统的脚本和示例。

## 📁 文件说明

### 核心模块

- **terminal_block_info.py** - 主模块，包含所有数据模型和功能
  - 新的数据模型（Cabinet, TerminalBlock, Device, Component等）
  - CabinetSystem系统管理
  - ConnectionGraph连接图
  - Draw.io导出功能
  - 向后兼容的TerminalInfo支持

### 测试和示例

- **test_new_model.py** - 数据模型单元测试
  - 测试所有核心类
  - 验证数据完整性
  - 运行: `python scripts/test_new_model.py`

- **example_cabinet_system.py** - 简单示例
  - 演示基本用法
  - 展示端子引用格式
  - 运行: `python scripts/example_cabinet_system.py`

- **example_complex_system.py** - 复杂系统示例
  - 3个机柜的完整系统
  - 23个连接关系
  - 真实场景演示
  - 运行: `python scripts/example_complex_system.py`

### 其他脚本

- **gen_graph.py** - 图生成工具
- **detect_cycles.py** - 环路检测
- **extract_netlist.py** - 网表提取
- **random_topo.py** - 随机拓扑生成

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pandas openpyxl
```

### 2. 创建简单系统

```python
from terminal_block_info import *

# 创建系统
system = CabinetSystem()

# 创建机柜
cabinet = Cabinet(number="CAB001", description="主控柜")

# 添加端子排
tb = TerminalBlock(name="TB1")
tb.add_terminal(Terminal(name="1", circuit_number="C001", cable_number="CAB001"))
cabinet.add_terminal_block(tb)

# 添加到系统
system.add_cabinet(cabinet)

# 验证
errors = system.validate_connections()
print("验证结果:", "通过" if not errors else errors)
```

### 3. 导出Draw.io图纸

```python
# 创建连接图
graph = ConnectionGraph()
graph.build_from_cabinet_system(system)

# 导出
from pathlib import Path
graph.export_system_to_drawio(Path("output"))
```

### 4. 从Excel读取（兼容旧格式）

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

## 📖 端子引用格式

### 端子排端子
```
格式: 机柜/端子排:端子号
示例: CAB001/TB_POWER:L1
```

### 装置端子
```
格式: 机柜/装置端子号
示例: CAB001/PLC_001/DI1
```

### 元件端子
```
格式: 机柜/元件:端子号
示例: CAB001/QF1:1
```

## 🔗 连接规则

### 端子排端子
- ✅ 直接互联本机柜内的其他端子
- ✅ 通过内部连线连接装置或元件端子
- ✅ 通过回路连接其他机柜（需回路号+电缆编号）

### 装置端子
- ✅ 直连其他装置端子
- ✅ 连接到端子排端子（作为出口）
- ✅ 连接到元件端子
- ❌ 不能直接通过回路号/电缆号接出

### 元件端子
- ✅ 根据类型有固定的内部连接
- ✅ 可连接到端子排或装置端子

### 回路连接
- ⚠️ **必须同时有回路号和电缆编号**
- ❌ 仅回路号或电缆编号相同不代表互联

## 📚 详细文档

- [完整数据模型文档](../docs/TERMINAL_BLOCK_MODEL.md)
- [重构总结](../docs/REFACTOR_SUMMARY.md)

## 🧪 运行测试

```bash
# 运行单元测试
python scripts/test_new_model.py

# 运行简单示例
python scripts/example_cabinet_system.py

# 运行复杂示例
python scripts/example_complex_system.py
```

## 💡 使用提示

1. **创建系统时**：先创建机柜，再添加端子排/装置/元件
2. **添加连接时**：使用完整的端子引用格式
3. **回路连接**：必须同时指定circuit_number和cable_number
4. **验证系统**：添加连接后调用validate_connections()
5. **导出图纸**：使用ConnectionGraph的export方法

## ❓ 常见问题

### Q: 如何处理装置中缺失的端子位置？
A: 只添加实际存在的端子即可，行列数会自动计算。

### Q: 元件的内部连接如何定义？
A: 使用add_internal_connection()方法，例如：
```python
switch.add_internal_connection("1", "2")
```

### Q: 如何确保回路连接正确？
A: 确保所有回路连接同时设置circuit_number和cable_number。

### Q: 旧的Excel文件还能用吗？
A: 可以！使用LegacyConverter转换为新模型。

## 🐛 问题报告

如有问题，请通过GitHub Issues报告。

## 📝 许可

遵循项目根目录的LICENSE文件。
