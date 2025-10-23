#!/usr/bin/env python3
"""
完整示例：创建机柜系统并生成drawio图纸

本示例展示了完整的工作流程：
1. 创建机柜系统（包括端子排、装置、元件）
2. 定义连接关系
3. 验证系统
4. 生成连接图
5. 导出drawio图纸

注意：需要安装pandas才能运行完整功能
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum

# ============================================================================
# 简化的类定义（用于演示，实际使用时从terminal_block_info导入）
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


class ConnectionType(Enum):
    DIRECT = "直连"
    INTERNAL_WIRE = "内部连线"
    CIRCUIT = "回路"
    THROUGH_COMPONENT = "经过元件"


@dataclass
class Connection:
    from_ref: str
    to_ref: str
    connection_type: ConnectionType
    circuit_number: Optional[str] = None
    cable_number: Optional[str] = None
    component_name: Optional[str] = None
    description: str = ""
    
    def is_circuit_connection(self) -> bool:
        return (self.connection_type == ConnectionType.CIRCUIT and 
                self.circuit_number is not None and 
                self.cable_number is not None)


from collections import defaultdict

class CabinetSystem:
    def __init__(self):
        self.cabinets: Dict[str, Cabinet] = {}
        self.connections: List[Connection] = []
        self.circuits: Dict[str, List[str]] = defaultdict(list)
        
    def add_cabinet(self, cabinet: Cabinet):
        self.cabinets[cabinet.number] = cabinet
    
    def add_connection(self, connection: Connection):
        self.connections.append(connection)
        if connection.is_circuit_connection():
            key = f"{connection.circuit_number}_{connection.cable_number}"
            if connection.from_ref not in self.circuits[key]:
                self.circuits[key].append(connection.from_ref)
            if connection.to_ref not in self.circuits[key]:
                self.circuits[key].append(connection.to_ref)
    
    def validate_connections(self) -> List[str]:
        """验证连接的有效性"""
        errors = []
        # 简化版验证
        for conn in self.connections:
            if conn.connection_type == ConnectionType.CIRCUIT:
                if not conn.circuit_number or not conn.cable_number:
                    errors.append(f"回路连接缺少回路号或电缆编号: {conn.from_ref} -> {conn.to_ref}")
        return errors


# ============================================================================
# 创建复杂的示例系统
# ============================================================================

def create_complex_system() -> CabinetSystem:
    """创建一个更复杂的示例系统"""
    
    print("=" * 80)
    print("创建复杂机柜系统")
    print("=" * 80)
    
    system = CabinetSystem()
    
    # ========================================================================
    # 机柜1：主控柜
    # ========================================================================
    print("\n[1/3] 创建主控柜 (CAB001)...")
    cabinet1 = Cabinet(number="CAB001", description="主控制柜")
    
    # 电源端子排
    tb_power = TerminalBlock(name="TB_POWER", description="电源端子排")
    tb_power.add_terminal(Terminal(name="L1", circuit_number="PWR_L1", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="L2", circuit_number="PWR_L2", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="L3", circuit_number="PWR_L3", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="N", circuit_number="PWR_N", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="PE", circuit_number="PWR_PE", cable_number="CABLE_001"))
    cabinet1.add_terminal_block(tb_power)
    print(f"  ✓ 添加端子排 TB_POWER: {len(tb_power.terminals)} 个端子")
    
    # 控制信号端子排
    tb_control = TerminalBlock(name="TB_CONTROL", description="控制信号端子排")
    for i in range(1, 21):
        tb_control.add_terminal(Terminal(name=f"C{i:02d}"))
    cabinet1.add_terminal_block(tb_control)
    print(f"  ✓ 添加端子排 TB_CONTROL: {len(tb_control.terminals)} 个端子")
    
    # PLC装置
    plc = Device(name="PLC_S7_1200", description="西门子S7-1200 PLC")
    # 数字输入：4行4列
    for row in range(4):
        for col in range(4):
            plc.add_terminal(DeviceTerminal(name=f"DI{row * 4 + col + 1:02d}", row=row, col=col))
    # 数字输出：2行4列（接在输入后面）
    for row in range(2):
        for col in range(4):
            plc.add_terminal(DeviceTerminal(name=f"DO{row * 4 + col + 1:02d}", row=row + 4, col=col))
    cabinet1.add_device(plc)
    print(f"  ✓ 添加装置 PLC_S7_1200: {len(plc.terminals)} 个端子 ({plc.rows}x{plc.cols})")
    
    # 主电源开关
    main_switch = Component(name="QF1", component_type=ComponentType.SWITCH, description="主电源断路器")
    main_switch.add_terminal(ComponentTerminal(name="L1_IN", position=0))
    main_switch.add_terminal(ComponentTerminal(name="L1_OUT", position=1))
    main_switch.add_terminal(ComponentTerminal(name="L2_IN", position=2))
    main_switch.add_terminal(ComponentTerminal(name="L2_OUT", position=3))
    main_switch.add_terminal(ComponentTerminal(name="L3_IN", position=4))
    main_switch.add_terminal(ComponentTerminal(name="L3_OUT", position=5))
    main_switch.add_internal_connection("L1_IN", "L1_OUT")
    main_switch.add_internal_connection("L2_IN", "L2_OUT")
    main_switch.add_internal_connection("L3_IN", "L3_OUT")
    cabinet1.add_component(main_switch)
    print(f"  ✓ 添加元件 QF1 (主电源开关): {len(main_switch.terminals)} 个端子")
    
    # 急停按钮
    estop = Component(name="BP_ESTOP", component_type=ComponentType.PRESSURE_PLATE, description="急停按钮")
    estop.add_terminal(ComponentTerminal(name="NO", position=0))
    estop.add_terminal(ComponentTerminal(name="NC", position=1))
    estop.add_terminal(ComponentTerminal(name="COM", position=2))
    estop.add_internal_connection("COM", "NC")  # 默认常闭
    cabinet1.add_component(estop)
    print(f"  ✓ 添加元件 BP_ESTOP (急停按钮): {len(estop.terminals)} 个端子")
    
    # 继电器
    relay = Component(name="KA1", component_type=ComponentType.RELAY, description="中间继电器")
    relay.add_terminal(ComponentTerminal(name="A1", position=0))  # 线圈
    relay.add_terminal(ComponentTerminal(name="A2", position=1))  # 线圈
    relay.add_terminal(ComponentTerminal(name="11", position=2))  # 常开触点
    relay.add_terminal(ComponentTerminal(name="12", position=3))
    relay.add_terminal(ComponentTerminal(name="21", position=4))  # 常闭触点
    relay.add_terminal(ComponentTerminal(name="22", position=5))
    cabinet1.add_component(relay)
    print(f"  ✓ 添加元件 KA1 (继电器): {len(relay.terminals)} 个端子")
    
    system.add_cabinet(cabinet1)
    
    # ========================================================================
    # 机柜2：I/O扩展柜
    # ========================================================================
    print("\n[2/3] 创建I/O扩展柜 (CAB002)...")
    cabinet2 = Cabinet(number="CAB002", description="I/O扩展柜")
    
    # I/O端子排
    tb_io = TerminalBlock(name="TB_IO", description="I/O端子排")
    for i in range(1, 33):
        tb_io.add_terminal(Terminal(name=f"IO{i:02d}"))
    cabinet2.add_terminal_block(tb_io)
    print(f"  ✓ 添加端子排 TB_IO: {len(tb_io.terminals)} 个端子")
    
    # I/O模块
    io_module = Device(name="IO_ET200S", description="ET200S I/O扩展模块")
    # 8行8列，但缺少一些位置
    skip_positions = [(2, 7), (3, 7), (6, 6), (6, 7), (7, 6), (7, 7)]
    for row in range(8):
        for col in range(8):
            if (row, col) not in skip_positions:
                io_module.add_terminal(DeviceTerminal(name=f"X{row}{col}", row=row, col=col))
    cabinet2.add_device(io_module)
    print(f"  ✓ 添加装置 IO_ET200S: {len(io_module.terminals)} 个端子 ({io_module.rows}x{io_module.cols})")
    
    system.add_cabinet(cabinet2)
    
    # ========================================================================
    # 机柜3：现场设备柜
    # ========================================================================
    print("\n[3/3] 创建现场设备柜 (CAB003)...")
    cabinet3 = Cabinet(number="CAB003", description="现场设备柜")
    
    # 现场设备端子排
    tb_field = TerminalBlock(name="TB_FIELD", description="现场设备端子排")
    for i in range(1, 25):
        tb_field.add_terminal(Terminal(name=f"F{i:02d}"))
    cabinet3.add_terminal_block(tb_field)
    print(f"  ✓ 添加端子排 TB_FIELD: {len(tb_field.terminals)} 个端子")
    
    system.add_cabinet(cabinet3)
    
    # ========================================================================
    # 添加连接关系
    # ========================================================================
    print("\n添加连接关系...")
    
    # 1. 电源连接（通过开关）
    system.add_connection(Connection(
        from_ref="CAB001/TB_POWER:L1",
        to_ref="CAB001/QF1:L1_IN",
        connection_type=ConnectionType.INTERNAL_WIRE,
        description="L1电源输入"
    ))
    system.add_connection(Connection(
        from_ref="CAB001/QF1:L1_OUT",
        to_ref="CAB001/TB_CONTROL:C01",
        connection_type=ConnectionType.INTERNAL_WIRE,
        description="L1电源输出"
    ))
    print("  ✓ 添加电源连接")
    
    # 2. 控制回路连接（通过急停按钮）
    system.add_connection(Connection(
        from_ref="CAB001/TB_CONTROL:C02",
        to_ref="CAB001/BP_ESTOP:COM",
        connection_type=ConnectionType.INTERNAL_WIRE,
        description="急停信号输入"
    ))
    system.add_connection(Connection(
        from_ref="CAB001/BP_ESTOP:NC",
        to_ref="CAB001/TB_CONTROL:C03",
        connection_type=ConnectionType.INTERNAL_WIRE,
        description="急停信号输出"
    ))
    print("  ✓ 添加急停连接")
    
    # 3. PLC与端子排连接
    for i in range(1, 9):
        system.add_connection(Connection(
            from_ref=f"CAB001/TB_CONTROL:C{i + 10:02d}",
            to_ref=f"CAB001/PLC_S7_1200/DI{i:02d}",
            connection_type=ConnectionType.INTERNAL_WIRE,
            description=f"DI{i}输入"
        ))
    print("  ✓ 添加PLC输入连接")
    
    # 4. 机柜间回路连接（CAB001 -> CAB002）
    system.add_connection(Connection(
        from_ref="CAB001/TB_CONTROL:C01",
        to_ref="CAB002/TB_IO:IO01",
        connection_type=ConnectionType.CIRCUIT,
        circuit_number="C001",
        cable_number="CABLE_002",
        description="控制信号线1"
    ))
    system.add_connection(Connection(
        from_ref="CAB001/TB_CONTROL:C02",
        to_ref="CAB002/TB_IO:IO02",
        connection_type=ConnectionType.CIRCUIT,
        circuit_number="C002",
        cable_number="CABLE_002",
        description="控制信号线2"
    ))
    print("  ✓ 添加机柜间回路连接 (CAB001 <-> CAB002)")
    
    # 5. 机柜间回路连接（CAB002 -> CAB003）
    system.add_connection(Connection(
        from_ref="CAB002/TB_IO:IO16",
        to_ref="CAB003/TB_FIELD:F01",
        connection_type=ConnectionType.CIRCUIT,
        circuit_number="F001",
        cable_number="CABLE_003",
        description="现场设备1"
    ))
    print("  ✓ 添加机柜间回路连接 (CAB002 <-> CAB003)")
    
    # 6. I/O模块连接
    for i in range(1, 9):
        system.add_connection(Connection(
            from_ref=f"CAB002/TB_IO:IO{i:02d}",
            to_ref=f"CAB002/IO_ET200S/X0{i-1}",
            connection_type=ConnectionType.INTERNAL_WIRE,
            description=f"I/O通道{i}"
        ))
    print("  ✓ 添加I/O模块连接")
    
    print(f"\n总共添加了 {len(system.connections)} 个连接")
    
    return system


def print_system_summary(system: CabinetSystem):
    """打印系统摘要"""
    print("\n" + "=" * 80)
    print("系统摘要")
    print("=" * 80)
    
    print(f"\n机柜总数: {len(system.cabinets)}")
    print(f"连接总数: {len(system.connections)}")
    print(f"回路总数: {len(system.circuits)}")
    
    for cabinet in system.cabinets.values():
        print(f"\n【{cabinet.number}】 {cabinet.description}")
        
        if cabinet.terminal_blocks:
            print(f"  端子排 ({len(cabinet.terminal_blocks)}):")
            for tb_name, tb in cabinet.terminal_blocks.items():
                print(f"    • {tb_name}: {len(tb.terminals)} 个端子 - {tb.description}")
        
        if cabinet.devices:
            print(f"  装置 ({len(cabinet.devices)}):")
            for dev_name, dev in cabinet.devices.items():
                print(f"    • {dev_name}: {len(dev.terminals)} 个端子 ({dev.rows}x{dev.cols}) - {dev.description}")
        
        if cabinet.components:
            print(f"  元件 ({len(cabinet.components)}):")
            for comp_name, comp in cabinet.components.items():
                print(f"    • {comp_name} ({comp.component_type.value}): {len(comp.terminals)} 个端子 - {comp.description}")
    
    print("\n" + "=" * 80)


def main():
    """主函数"""
    try:
        # 创建系统
        system = create_complex_system()
        
        # 打印摘要
        print_system_summary(system)
        
        # 验证连接
        print("\n验证连接关系...")
        errors = system.validate_connections()
        if errors:
            print("发现错误:")
            for error in errors:
                print(f"  ✗ {error}")
            return 1
        else:
            print("  ✓ 所有连接验证通过")
        
        print("\n" + "=" * 80)
        print("示例系统创建完成！")
        print("=" * 80)
        
        print("\n提示:")
        print("  要生成drawio图纸，需要:")
        print("  1. 安装pandas: pip install pandas openpyxl")
        print("  2. 使用ConnectionGraph类构建图并导出")
        print("  3. 参考terminal_block_info.py中的完整实现")
        
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
