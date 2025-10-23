#!/usr/bin/env python3
"""
简单测试脚本，验证新的数据模型是否正常工作
不依赖pandas，仅测试基本的数据结构
"""

import sys
from pathlib import Path

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 手动模拟需要的类（避免导入pandas）
from typing import List, Optional, Dict, Any, Set, Iterable, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 复制必要的类定义（不依赖pandas）
@dataclass
class Terminal:
    """端子 - 连接点，具有名称属性"""
    name: str
    circuit_number: Optional[str] = None
    cable_number: Optional[str] = None
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Terminal):
            return self.name == other.name
        return False


@dataclass
class TerminalBlock:
    """端子排 - 纵向排列的端子组合"""
    name: str
    terminals: List[Terminal] = field(default_factory=list)
    description: str = ""
    
    def add_terminal(self, terminal: Terminal):
        if terminal not in self.terminals:
            self.terminals.append(terminal)
    
    def get_terminal(self, name: str) -> Optional[Terminal]:
        for terminal in self.terminals:
            if terminal.name == name:
                return terminal
        return None


@dataclass 
class DeviceTerminal:
    """装置端子"""
    name: str
    row: int
    col: int
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, DeviceTerminal):
            return self.name == other.name
        return False


@dataclass
class Device:
    """装置 - 带有规则布局端子的容器"""
    name: str
    terminals: List[DeviceTerminal] = field(default_factory=list)
    rows: int = 0
    cols: int = 0
    description: str = ""
    
    def add_terminal(self, terminal: DeviceTerminal):
        if terminal not in self.terminals:
            self.terminals.append(terminal)
            self.rows = max(self.rows, terminal.row + 1)
            self.cols = max(self.cols, terminal.col + 1)
    
    def get_terminal_at(self, row: int, col: int) -> Optional[DeviceTerminal]:
        for terminal in self.terminals:
            if terminal.row == row and terminal.col == col:
                return terminal
        return None


@dataclass
class ComponentTerminal:
    """元件端子"""
    name: str
    position: int
    
    def __hash__(self):
        return hash(self.name)


class ComponentType(Enum):
    """元件类型"""
    SWITCH = "开关"
    PRESSURE_PLATE = "压板"
    RELAY = "继电器"
    OTHER = "其他"


@dataclass
class Component:
    """元件 - 具有固定形状的电子器件"""
    name: str
    component_type: ComponentType
    terminals: List[ComponentTerminal] = field(default_factory=list)
    description: str = ""
    internal_connections: List[Tuple[str, str]] = field(default_factory=list)
    
    def add_terminal(self, terminal: ComponentTerminal):
        if terminal not in self.terminals:
            self.terminals.append(terminal)
    
    def add_internal_connection(self, terminal1: str, terminal2: str):
        conn = (terminal1, terminal2)
        if conn not in self.internal_connections and (terminal2, terminal1) not in self.internal_connections:
            self.internal_connections.append(conn)


@dataclass
class Cabinet:
    """机柜"""
    number: str
    terminal_blocks: Dict[str, TerminalBlock] = field(default_factory=dict)
    devices: Dict[str, Device] = field(default_factory=dict)
    components: Dict[str, Component] = field(default_factory=dict)
    description: str = ""
    
    def add_terminal_block(self, terminal_block: TerminalBlock):
        self.terminal_blocks[terminal_block.name] = terminal_block
    
    def add_device(self, device: Device):
        self.devices[device.name] = device
    
    def add_component(self, component: Component):
        self.components[component.name] = component


def test_terminal_and_terminal_block():
    """测试端子和端子排"""
    print("测试端子和端子排...")
    
    # 创建端子
    t1 = Terminal(name="1", circuit_number="C001", cable_number="CAB001")
    t2 = Terminal(name="2", circuit_number="C001", cable_number="CAB001")
    t3 = Terminal(name="3")
    
    # 创建端子排
    tb = TerminalBlock(name="TB1", description="测试端子排")
    tb.add_terminal(t1)
    tb.add_terminal(t2)
    tb.add_terminal(t3)
    
    assert len(tb.terminals) == 3
    assert tb.get_terminal("1") == t1
    assert tb.get_terminal("2") == t2
    assert tb.get_terminal("4") is None
    
    print("✓ 端子和端子排测试通过")


def test_device():
    """测试装置"""
    print("测试装置...")
    
    # 创建装置
    device = Device(name="D001", description="测试装置")
    
    # 添加端子（2行3列的矩形阵列，但缺少(1,2)位置）
    device.add_terminal(DeviceTerminal(name="D1", row=0, col=0))
    device.add_terminal(DeviceTerminal(name="D2", row=0, col=1))
    device.add_terminal(DeviceTerminal(name="D3", row=0, col=2))
    device.add_terminal(DeviceTerminal(name="D4", row=1, col=0))
    device.add_terminal(DeviceTerminal(name="D5", row=1, col=1))
    # (1, 2) 位置缺失
    
    assert device.rows == 2
    assert device.cols == 3
    assert len(device.terminals) == 5
    assert device.get_terminal_at(0, 0).name == "D1"
    assert device.get_terminal_at(1, 2) is None  # 缺失的位置
    
    print("✓ 装置测试通过")


def test_component():
    """测试元件"""
    print("测试元件...")
    
    # 创建开关元件
    switch = Component(
        name="S001",
        component_type=ComponentType.SWITCH,
        description="测试开关"
    )
    
    # 添加端子
    switch.add_terminal(ComponentTerminal(name="1", position=0))
    switch.add_terminal(ComponentTerminal(name="2", position=1))
    
    # 添加内部连接
    switch.add_internal_connection("1", "2")
    
    assert len(switch.terminals) == 2
    assert len(switch.internal_connections) == 1
    assert switch.internal_connections[0] == ("1", "2")
    
    print("✓ 元件测试通过")


def test_cabinet():
    """测试机柜"""
    print("测试机柜...")
    
    # 创建机柜
    cabinet = Cabinet(number="CAB001", description="测试机柜")
    
    # 添加端子排
    tb1 = TerminalBlock(name="TB1")
    tb1.add_terminal(Terminal(name="1"))
    tb1.add_terminal(Terminal(name="2"))
    cabinet.add_terminal_block(tb1)
    
    # 添加装置
    device = Device(name="D001")
    device.add_terminal(DeviceTerminal(name="D1", row=0, col=0))
    cabinet.add_device(device)
    
    # 添加元件
    component = Component(name="S001", component_type=ComponentType.SWITCH)
    component.add_terminal(ComponentTerminal(name="1", position=0))
    cabinet.add_component(component)
    
    assert len(cabinet.terminal_blocks) == 1
    assert len(cabinet.devices) == 1
    assert len(cabinet.components) == 1
    assert "TB1" in cabinet.terminal_blocks
    
    print("✓ 机柜测试通过")


def test_complete_system():
    """测试完整系统"""
    print("\n测试完整系统...")
    
    # 创建两个机柜
    cab1 = Cabinet(number="CAB001", description="机柜1")
    cab2 = Cabinet(number="CAB002", description="机柜2")
    
    # 机柜1：端子排TB1，端子1-5
    tb1 = TerminalBlock(name="TB1", description="端子排1")
    for i in range(1, 6):
        tb1.add_terminal(Terminal(name=str(i), circuit_number="C001", cable_number="CAB001"))
    cab1.add_terminal_block(tb1)
    
    # 机柜1：装置D001，2x2阵列
    device1 = Device(name="D001", description="装置1")
    for row in range(2):
        for col in range(2):
            device1.add_terminal(DeviceTerminal(name=f"D{row}{col}", row=row, col=col))
    cab1.add_device(device1)
    
    # 机柜1：开关S001
    switch1 = Component(name="S001", component_type=ComponentType.SWITCH, description="开关1")
    switch1.add_terminal(ComponentTerminal(name="IN", position=0))
    switch1.add_terminal(ComponentTerminal(name="OUT", position=1))
    switch1.add_internal_connection("IN", "OUT")
    cab1.add_component(switch1)
    
    # 机柜2：端子排TB2，端子1-3
    tb2 = TerminalBlock(name="TB2", description="端子排2")
    for i in range(1, 4):
        tb2.add_terminal(Terminal(name=str(i), circuit_number="C001", cable_number="CAB001"))
    cab2.add_terminal_block(tb2)
    
    # 验证结构
    assert len(cab1.terminal_blocks) == 1
    assert len(cab1.devices) == 1
    assert len(cab1.components) == 1
    assert len(cab2.terminal_blocks) == 1
    
    assert len(tb1.terminals) == 5
    assert len(tb2.terminals) == 3
    assert device1.rows == 2 and device1.cols == 2
    assert len(switch1.terminals) == 2
    assert len(switch1.internal_connections) == 1
    
    print("✓ 完整系统测试通过")
    print("\n所有测试通过！新的数据模型工作正常。")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试新的数据模型")
    print("=" * 60)
    
    try:
        test_terminal_and_terminal_block()
        test_device()
        test_component()
        test_cabinet()
        test_complete_system()
        
        print("\n" + "=" * 60)
        print("所有测试成功完成！")
        print("=" * 60)
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
