#!/usr/bin/env python3
"""
示例：使用新的数据模型创建机柜系统

本示例展示了如何使用新的数据模型来创建一个完整的机柜系统，
包括端子排、装置、元件以及它们之间的连接关系。
"""

import sys
from pathlib import Path

# 为了演示，我们在这里定义简化版的类（实际使用时应导入terminal_block_info模块）
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# 简化的类定义（实际使用时从terminal_block_info导入）
# ============================================================================

@dataclass
class Terminal:
    name: str
    circuit_number: Optional[str] = None
    cable_number: Optional[str] = None


@dataclass
class TerminalBlock:
    name: str
    terminals: List[Terminal] = field(default_factory=list)
    description: str = ""
    
    def add_terminal(self, terminal: Terminal):
        if terminal not in self.terminals:
            self.terminals.append(terminal)


@dataclass 
class DeviceTerminal:
    name: str
    row: int
    col: int


@dataclass
class Device:
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


@dataclass
class ComponentTerminal:
    name: str
    position: int


class ComponentType(Enum):
    SWITCH = "开关"
    PRESSURE_PLATE = "压板"
    RELAY = "继电器"
    OTHER = "其他"


@dataclass
class Component:
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
        if conn not in self.internal_connections:
            self.internal_connections.append(conn)


@dataclass
class Cabinet:
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


# ============================================================================
# 示例：创建一个完整的机柜系统
# ============================================================================

def create_example_system():
    """创建一个示例机柜系统"""
    
    print("=" * 80)
    print("示例：创建机柜系统")
    print("=" * 80)
    
    # ========================================================================
    # 机柜1：控制柜
    # ========================================================================
    print("\n创建机柜1 (控制柜)...")
    cabinet1 = Cabinet(number="CAB001", description="主控制柜")
    
    # 端子排1：电源端子排
    print("  添加端子排 TB_POWER (电源端子排)...")
    tb_power = TerminalBlock(name="TB_POWER", description="电源端子排")
    tb_power.add_terminal(Terminal(name="L1", circuit_number="PWR_L1", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="L2", circuit_number="PWR_L2", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="L3", circuit_number="PWR_L3", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="N", circuit_number="PWR_N", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="PE", circuit_number="PWR_PE", cable_number="CABLE_001"))
    cabinet1.add_terminal_block(tb_power)
    print(f"    端子排包含 {len(tb_power.terminals)} 个端子")
    
    # 端子排2：信号端子排
    print("  添加端子排 TB_SIGNAL (信号端子排)...")
    tb_signal = TerminalBlock(name="TB_SIGNAL", description="信号端子排")
    for i in range(1, 11):
        tb_signal.add_terminal(Terminal(name=f"S{i}", circuit_number=f"SIG_{i:02d}"))
    cabinet1.add_terminal_block(tb_signal)
    print(f"    端子排包含 {len(tb_signal.terminals)} 个端子")
    
    # 装置1：PLC模块
    print("  添加装置 PLC_001 (PLC模块)...")
    plc = Device(name="PLC_001", description="西门子S7-1200 PLC")
    # 输入端子：4行4列
    for row in range(4):
        for col in range(4):
            term_name = f"DI{row * 4 + col + 1}"
            plc.add_terminal(DeviceTerminal(name=term_name, row=row, col=col))
    cabinet1.add_device(plc)
    print(f"    PLC包含 {len(plc.terminals)} 个端子 ({plc.rows}x{plc.cols} 阵列)")
    
    # 元件1：主电源开关
    print("  添加元件 QF1 (主电源开关)...")
    main_switch = Component(
        name="QF1",
        component_type=ComponentType.SWITCH,
        description="主电源断路器"
    )
    main_switch.add_terminal(ComponentTerminal(name="1", position=0))
    main_switch.add_terminal(ComponentTerminal(name="2", position=1))
    main_switch.add_internal_connection("1", "2")
    cabinet1.add_component(main_switch)
    print(f"    开关包含 {len(main_switch.terminals)} 个端子")
    
    # 元件2：急停压板
    print("  添加元件 BP1 (急停压板)...")
    estop_button = Component(
        name="BP1",
        component_type=ComponentType.PRESSURE_PLATE,
        description="急停按钮"
    )
    estop_button.add_terminal(ComponentTerminal(name="NO", position=0))  # 常开
    estop_button.add_terminal(ComponentTerminal(name="NC", position=1))  # 常闭
    estop_button.add_terminal(ComponentTerminal(name="COM", position=2)) # 公共端
    estop_button.add_internal_connection("COM", "NC")  # 默认连接常闭
    cabinet1.add_component(estop_button)
    print(f"    急停按钮包含 {len(estop_button.terminals)} 个端子")
    
    # ========================================================================
    # 机柜2：I/O扩展柜
    # ========================================================================
    print("\n创建机柜2 (I/O扩展柜)...")
    cabinet2 = Cabinet(number="CAB002", description="I/O扩展柜")
    
    # 端子排：I/O端子排
    print("  添加端子排 TB_IO (I/O端子排)...")
    tb_io = TerminalBlock(name="TB_IO", description="I/O端子排")
    for i in range(1, 21):
        tb_io.add_terminal(Terminal(name=f"IO{i}", circuit_number=f"IO_{i:02d}"))
    cabinet2.add_terminal_block(tb_io)
    print(f"    端子排包含 {len(tb_io.terminals)} 个端子")
    
    # 装置：I/O模块
    print("  添加装置 IO_MODULE_001 (I/O模块)...")
    io_module = Device(name="IO_MODULE_001", description="I/O扩展模块")
    # 8行4列，但缺少一些位置
    for row in range(8):
        for col in range(4):
            # 跳过某些位置（模拟实际布局）
            if (row, col) in [(2, 3), (5, 3), (7, 2), (7, 3)]:
                continue
            term_name = f"X{row}{col}"
            io_module.add_terminal(DeviceTerminal(name=term_name, row=row, col=col))
    cabinet2.add_device(io_module)
    print(f"    I/O模块包含 {len(io_module.terminals)} 个端子 ({io_module.rows}x{io_module.cols} 阵列)")
    
    # ========================================================================
    # 显示系统摘要
    # ========================================================================
    print("\n" + "=" * 80)
    print("系统摘要")
    print("=" * 80)
    
    cabinets = [cabinet1, cabinet2]
    for cab in cabinets:
        print(f"\n机柜 {cab.number} - {cab.description}")
        print(f"  端子排数量: {len(cab.terminal_blocks)}")
        for tb_name, tb in cab.terminal_blocks.items():
            print(f"    - {tb_name}: {len(tb.terminals)} 个端子")
        print(f"  装置数量: {len(cab.devices)}")
        for dev_name, dev in cab.devices.items():
            print(f"    - {dev_name}: {len(dev.terminals)} 个端子 ({dev.rows}x{dev.cols})")
        print(f"  元件数量: {len(cab.components)}")
        for comp_name, comp in cab.components.items():
            print(f"    - {comp_name} ({comp.component_type.value}): {len(comp.terminals)} 个端子")
    
    print("\n" + "=" * 80)
    print("示例系统创建完成！")
    print("=" * 80)
    
    return cabinet1, cabinet2


def demonstrate_terminal_references():
    """演示端子引用格式"""
    print("\n" + "=" * 80)
    print("端子引用格式说明")
    print("=" * 80)
    
    print("\n完整描述一个端子的格式：")
    print("  1. 端子排端子：  机柜/端子排:端子号")
    print("     示例: CAB001/TB_POWER:L1")
    print("           ^^^^^^  ^^^^^^^^ ^^")
    print("           机柜    端子排   端子号")
    
    print("\n  2. 装置端子：    机柜/装置端子号")
    print("     示例: CAB001/PLC_001/DI1")
    print("           ^^^^^^  ^^^^^^^^ ^^^")
    print("           机柜    装置     端子号")
    
    print("\n  3. 元件端子：    机柜/元件:端子号")
    print("     示例: CAB001/QF1:1")
    print("           ^^^^^^  ^^^ ^")
    print("           机柜    元件 端子号")
    
    print("\n连接规则：")
    print("  - 端子排内的端子可以：")
    print("    * 直接互联本机柜内的其他端子")
    print("    * 通过内部连线连接到所在机柜内的装置或元件的端子")
    print("    * 通过回路连接到其他机柜的端子（需要回路号+电缆编号）")
    
    print("\n  - 装置内的端子可以：")
    print("    * 直连其他装置端子")
    print("    * 连接到端子排端子（作为出口）")
    print("    * 连接到元件端子")
    print("    * 不能直接通过回路号/电缆号接出（必须通过端子排）")
    
    print("\n  - 元件内的端子：")
    print("    * 根据元件类型有固定的内部连接关系")
    print("    * 可以连接到端子排端子或装置端子")
    
    print("\n  - 回路连接：")
    print("    * 必须同时具有回路号和电缆编号才能代表互联")
    print("    * 仅回路号或电缆编号相同不能代表互联")


def main():
    """主函数"""
    try:
        # 创建示例系统
        cabinet1, cabinet2 = create_example_system()
        
        # 演示端子引用格式
        demonstrate_terminal_references()
        
        print("\n示例运行成功！")
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
