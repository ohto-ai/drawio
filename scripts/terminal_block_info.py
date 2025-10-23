import pandas as pd
from typing import List, Optional, Dict, Any, Set, Iterable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from pathlib import Path
from collections import deque, defaultdict
from xml.sax.saxutils import escape
import os
import io


# ============================================================================
# Core Data Model Classes
# ============================================================================

@dataclass
class Terminal:
    """端子 - 连接点，具有名称属性"""
    name: str                         # 端子名称
    circuit_number: Optional[str] = None  # 回路号
    cable_number: Optional[str] = None    # 电缆编号
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Terminal):
            return self.name == other.name
        return False


@dataclass
class TerminalBlock:
    """端子排 - 纵向排列的端子组合，带有名称属性"""
    name: str                         # 端子排名称
    terminals: List[Terminal] = field(default_factory=list)  # 纵向排列的端子列表
    description: str = ""             # 端子排说明
    
    def add_terminal(self, terminal: Terminal):
        """添加端子到端子排"""
        if terminal not in self.terminals:
            self.terminals.append(terminal)
    
    def get_terminal(self, name: str) -> Optional[Terminal]:
        """根据名称获取端子"""
        for terminal in self.terminals:
            if terminal.name == name:
                return terminal
        return None


@dataclass 
class DeviceTerminal:
    """装置端子 - 装置内的端子，带有位置信息"""
    name: str                         # 端子名称（机柜内独立名称）
    row: int                          # 在装置中的行位置
    col: int                          # 在装置中的列位置
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, DeviceTerminal):
            return self.name == other.name
        return False


@dataclass
class Device:
    """装置 - 带有规则布局端子的容器，一般是矩形阵列"""
    name: str                         # 装置名称
    terminals: List[DeviceTerminal] = field(default_factory=list)  # 端子列表
    rows: int = 0                     # 行数
    cols: int = 0                     # 列数
    description: str = ""             # 装置说明
    
    def add_terminal(self, terminal: DeviceTerminal):
        """添加端子到装置"""
        if terminal not in self.terminals:
            self.terminals.append(terminal)
            # 更新行列数
            self.rows = max(self.rows, terminal.row + 1)
            self.cols = max(self.cols, terminal.col + 1)
    
    def get_terminal(self, name: str) -> Optional[DeviceTerminal]:
        """根据名称获取端子"""
        for terminal in self.terminals:
            if terminal.name == name:
                return terminal
        return None
    
    def get_terminal_at(self, row: int, col: int) -> Optional[DeviceTerminal]:
        """获取指定位置的端子"""
        for terminal in self.terminals:
            if terminal.row == row and terminal.col == col:
                return terminal
        return None


@dataclass
class ComponentTerminal:
    """元件端子 - 元件上的固定端子"""
    name: str                         # 端子名称
    position: int                     # 端子位置索引
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, ComponentTerminal):
            return self.name == other.name
        return False


class ComponentType(Enum):
    """元件类型"""
    SWITCH = "开关"
    PRESSURE_PLATE = "压板"
    RELAY = "继电器"
    OTHER = "其他"


@dataclass
class Component:
    """元件 - 具有固定形状的电子器件（如开关、压板）"""
    name: str                         # 元件名称
    component_type: ComponentType     # 元件类型
    terminals: List[ComponentTerminal] = field(default_factory=list)  # 端子列表
    description: str = ""             # 元件说明
    
    # 元件内部连接关系（端子名称对）
    internal_connections: List[Tuple[str, str]] = field(default_factory=list)
    
    def add_terminal(self, terminal: ComponentTerminal):
        """添加端子到元件"""
        if terminal not in self.terminals:
            self.terminals.append(terminal)
    
    def get_terminal(self, name: str) -> Optional[ComponentTerminal]:
        """根据名称获取端子"""
        for terminal in self.terminals:
            if terminal.name == name:
                return terminal
        return None
    
    def add_internal_connection(self, terminal1: str, terminal2: str):
        """添加元件内部连接"""
        conn = (terminal1, terminal2)
        if conn not in self.internal_connections and (terminal2, terminal1) not in self.internal_connections:
            self.internal_connections.append(conn)


@dataclass
class Cabinet:
    """机柜 - 包含端子排、装置和元件的容器"""
    number: str                       # 机柜编号
    terminal_blocks: Dict[str, TerminalBlock] = field(default_factory=dict)  # 端子排字典
    devices: Dict[str, Device] = field(default_factory=dict)  # 装置字典
    components: Dict[str, Component] = field(default_factory=dict)  # 元件字典
    description: str = ""             # 机柜说明
    
    def add_terminal_block(self, terminal_block: TerminalBlock):
        """添加端子排到机柜"""
        self.terminal_blocks[terminal_block.name] = terminal_block
    
    def add_device(self, device: Device):
        """添加装置到机柜"""
        self.devices[device.name] = device
    
    def add_component(self, component: Component):
        """添加元件到机柜"""
        self.components[component.name] = component
    
    def get_terminal_block(self, name: str) -> Optional[TerminalBlock]:
        """根据名称获取端子排"""
        return self.terminal_blocks.get(name)
    
    def get_device(self, name: str) -> Optional[Device]:
        """根据名称获取装置"""
        return self.devices.get(name)
    
    def get_component(self, name: str) -> Optional[Component]:
        """根据名称获取元件"""
        return self.components.get(name)


class ConnectionType(Enum):
    """连接类型"""
    DIRECT = "直连"                   # 端子直接互联
    INTERNAL_WIRE = "内部连线"        # 机柜内部连线
    CIRCUIT = "回路"                  # 通过回路号连接
    THROUGH_COMPONENT = "经过元件"    # 通过元件连接


@dataclass
class Connection:
    """连接关系 - 描述两个端子之间的连接"""
    from_ref: str                     # 源端子引用（格式：机柜/端子排:端子号 或 机柜/装置端子号 或 机柜/元件:端子号）
    to_ref: str                       # 目标端子引用
    connection_type: ConnectionType   # 连接类型
    circuit_number: Optional[str] = None  # 回路号（用于回路连接）
    cable_number: Optional[str] = None    # 电缆编号（用于回路连接）
    component_name: Optional[str] = None  # 元件名称（用于经过元件的连接）
    description: str = ""             # 连接说明
    
    def is_circuit_connection(self) -> bool:
        """判断是否为回路连接（需要回路号和电缆编号都相同）"""
        return (self.connection_type == ConnectionType.CIRCUIT and 
                self.circuit_number is not None and 
                self.cable_number is not None)


# ============================================================================
# Legacy TerminalInfo for backward compatibility
# ============================================================================

@dataclass
class TerminalInfo:
    """端子排信息数据类（保留用于向后兼容）"""
    cabinet_name: str                # 机柜名称
    circuit_number: str              # 回路号
    terminal_block_desc: str         # 端子排说明
    terminal_block: str              # 端子排
    terminal_number: str             # 端子号
    side: str                        # 左侧/右侧
    internal_wiring: List[str]       # 内部配线
    interconnect_terminal: List[str] # 互联端子号
    function_desc: str               # 功能说明
    external_wiring: str             # 外部接线
    cable_core_number: str           # 电缆芯编号
    cable_number: str                # 电缆编号
    core_number: str                 # 芯号
    cable_model: str                 # 电缆型号
    opposite_device_number: str      # 对侧设备编号
    opposite_device_name: str        # 对侧设备名称
    remarks: str                     # 备注
    col_wire_text: str               # COLWIRETExT
    cable_type: str                  # 线缆型号

    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TerminalInfo':
        """从字典创建TerminalInfo对象"""
        def safe_str(value) -> str:
            """安全转换为字符串并去除空格"""
            if value is None or pd.isna(value):
                return ""
            return str(value).strip()

        def split_to_list(value: str) -> List[str]:
            """将字符串按分隔符分割为列表，并清理空值。支持 ';' 和 ','（包括中文逗号/分号）作为分隔符。"""
            if not value:
                return []
            parts = re.split(r'[;,，；/ ]', value)
            return [item.strip() for item in parts if item.strip()]

        return cls(
            cabinet_name=safe_str(data.get('机柜名称', '')),
            circuit_number=safe_str(data.get('回路号', '')),
            terminal_block_desc=safe_str(data.get('端子排说明', '')),
            terminal_block=safe_str(data.get('端子排', '')),
            terminal_number=safe_str(data.get('端子号', '')),
            side=safe_str(data.get('左侧/右侧', '')),
            internal_wiring=split_to_list(safe_str(data.get('内部配线', ''))),
            interconnect_terminal=split_to_list(safe_str(data.get('互联端子号', ''))),
            function_desc=safe_str(data.get('功能说明', '')),
            external_wiring=safe_str(data.get('外部接线', '')),
            cable_core_number=safe_str(data.get('电缆芯编号', '')),
            cable_number=safe_str(data.get('电缆编号', '')),
            core_number=safe_str(data.get('芯号', '')),
            cable_model=safe_str(data.get('电缆型号', '')),
            opposite_device_number=safe_str(data.get('对侧设备编号', '')),
            opposite_device_name=safe_str(data.get('对侧设备名称', '')),
            remarks=safe_str(data.get('备注', '')),
            col_wire_text=safe_str(data.get('COLWIRETExT', '')),
            cable_type=safe_str(data.get('线缆型号', '')),
        )


# ============================================================================
# System Level Classes
# ============================================================================

class CabinetSystem:
    """机柜系统 - 管理多个机柜及其之间的连接关系"""
    
    def __init__(self):
        self.cabinets: Dict[str, Cabinet] = {}  # 机柜字典
        self.connections: List[Connection] = []  # 连接列表
        self.circuits: Dict[str, List[str]] = defaultdict(list)  # 回路号 -> 端子引用列表
        
    def add_cabinet(self, cabinet: Cabinet):
        """添加机柜到系统"""
        self.cabinets[cabinet.number] = cabinet
    
    def get_cabinet(self, number: str) -> Optional[Cabinet]:
        """根据编号获取机柜"""
        return self.cabinets.get(number)
    
    def add_connection(self, connection: Connection):
        """添加连接关系"""
        self.connections.append(connection)
        
        # 如果是回路连接，添加到回路字典
        if connection.is_circuit_connection():
            key = f"{connection.circuit_number}_{connection.cable_number}"
            if connection.from_ref not in self.circuits[key]:
                self.circuits[key].append(connection.from_ref)
            if connection.to_ref not in self.circuits[key]:
                self.circuits[key].append(connection.to_ref)
    
    def parse_terminal_ref(self, ref: str) -> Optional[Tuple[str, str, str, str]]:
        """
        解析端子引用字符串
        格式:
          - 机柜/端子排:端子号 (terminal block terminal)
          - 机柜/装置端子号 (device terminal)
          - 机柜/元件:端子号 (component terminal)
        
        返回: (cabinet_number, type, container_name, terminal_name)
          type: 'terminal_block' | 'device' | 'component'
        """
        ref = (ref or "").strip()
        if not ref:
            return None
        
        # 尝试匹配 机柜/容器:端子 格式
        if "/" in ref and ":" in ref:
            parts = ref.split("/", 1)
            cabinet = parts[0].strip()
            rest = parts[1].strip()
            
            if ":" in rest:
                container, terminal = rest.split(":", 1)
                # 判断是端子排还是元件
                # 通常元件名称会包含类型标识，端子排是纯编号或名称
                # 这里简单假设：如果container在机柜的components中存在，则为元件
                cab = self.get_cabinet(cabinet)
                if cab:
                    if container in cab.components:
                        return (cabinet, "component", container.strip(), terminal.strip())
                    elif container in cab.terminal_blocks:
                        return (cabinet, "terminal_block", container.strip(), terminal.strip())
            else:
                # 格式为 机柜/端子号，可能是装置端子
                return (cabinet, "device", "", rest)
        
        return None
    
    def get_terminal_by_ref(self, ref: str) -> Optional[Any]:
        """根据引用获取端子对象"""
        parsed = self.parse_terminal_ref(ref)
        if not parsed:
            return None
        
        cabinet_num, term_type, container, terminal_name = parsed
        cabinet = self.get_cabinet(cabinet_num)
        if not cabinet:
            return None
        
        if term_type == "terminal_block":
            tb = cabinet.get_terminal_block(container)
            return tb.get_terminal(terminal_name) if tb else None
        elif term_type == "device":
            # 装置端子需要遍历所有装置
            for device in cabinet.devices.values():
                t = device.get_terminal(terminal_name)
                if t:
                    return t
            return None
        elif term_type == "component":
            comp = cabinet.get_component(container)
            return comp.get_terminal(terminal_name) if comp else None
        
        return None
    
    def get_connected_terminals(self, ref: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """
        获取与指定端子连接的所有端子引用（递归查找）
        
        Args:
            ref: 端子引用
            visited: 已访问的端子集合（用于避免循环）
        
        Returns:
            连接的端子引用集合
        """
        if visited is None:
            visited = set()
        
        if ref in visited:
            return visited
        
        visited.add(ref)
        connected = set([ref])
        
        # 查找直接连接
        for conn in self.connections:
            if conn.from_ref == ref and conn.to_ref not in visited:
                connected.update(self.get_connected_terminals(conn.to_ref, visited))
            elif conn.to_ref == ref and conn.from_ref not in visited:
                connected.update(self.get_connected_terminals(conn.from_ref, visited))
        
        # 查找回路连接
        for conn in self.connections:
            if conn.is_circuit_connection():
                if conn.from_ref == ref or conn.to_ref == ref:
                    # 找到同一回路的所有端子
                    key = f"{conn.circuit_number}_{conn.cable_number}"
                    for term_ref in self.circuits[key]:
                        if term_ref not in visited:
                            connected.update(self.get_connected_terminals(term_ref, visited))
        
        return connected
    
    def get_connections_by_circuit(self, circuit_number: str, cable_number: Optional[str] = None) -> List[Connection]:
        """获取指定回路的所有连接"""
        result = []
        for conn in self.connections:
            if conn.circuit_number == circuit_number:
                if cable_number is None or conn.cable_number == cable_number:
                    result.append(conn)
        return result
    
    def validate_connections(self) -> List[str]:
        """
        验证连接关系的有效性
        
        Returns:
            错误信息列表
        """
        errors = []
        
        for conn in self.connections:
            # 检查源端子是否存在
            if not self.get_terminal_by_ref(conn.from_ref):
                errors.append(f"源端子不存在: {conn.from_ref}")
            
            # 检查目标端子是否存在
            if not self.get_terminal_by_ref(conn.to_ref):
                errors.append(f"目标端子不存在: {conn.to_ref}")
            
            # 检查回路连接是否同时有回路号和电缆编号
            if conn.connection_type == ConnectionType.CIRCUIT:
                if not conn.circuit_number or not conn.cable_number:
                    errors.append(f"回路连接缺少回路号或电缆编号: {conn.from_ref} -> {conn.to_ref}")
        
        return errors


class TerminalBlockReader:
    """端子排信息读取器（保留用于向后兼容）"""
    
    def __init__(self):
        pass
    
    def read_from_excel(self, file_path: str, cabinet_name = None, sheet_name: str = None, header_row: int = 0) -> List[TerminalInfo]:
        """
        从Excel文件读取端子排信息
        
        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称，默认为第一个工作表
            header_row: 表头所在行，默认为0
            
        Returns:
            List[TerminalInfo]: 端子排信息列表
        """
        try:
            print(f"正在读取文件: {file_path}")
            
            if cabinet_name is None:
                cabinet_name = Path(file_path).stem
                print(f"自动设置机柜名称为: {cabinet_name}")
            
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            else:
                df = pd.read_excel(file_path, header=header_row)
            
            print(f"成功读取数据，共 {len(df)} 行")
            print(f"列名: {list(df.columns)}")
            
            return self._process_dataframe(df, cabinet_name)
            
        except Exception as e:
            print(f"读取Excel文件失败: {e}")
            return []
    
    def read_from_csv(self, file_path: str, encoding: str = 'utf-8') -> List[TerminalInfo]:
        """
        从CSV文件读取端子排信息
        
        Args:
            file_path: CSV文件路径
            encoding: 文件编码，默认为utf-8
            
        Returns:
            List[TerminalInfo]: 端子排信息列表
        """
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            print(f"成功读取CSV数据，共 {len(df)} 行")
            return self._process_dataframe(df)
            
        except Exception as e:
            print(f"读取CSV文件失败: {e}")
            return []
    
    def _process_dataframe(self, df: pd.DataFrame, cabinet_name: str) -> List[TerminalInfo]:
        """处理DataFrame数据"""
        terminal_blocks = []
        
        # 清理列名（去除空格和特殊字符）
        df.columns = df.columns.str.strip()
        print(f"清理后列名: {list(df.columns)}")
        
        # 显示前几行数据用于调试
        print("\n前3行数据示例:")
        print(df.head(3))
        
        successful_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                terminal_info = TerminalInfo.from_dict(row.to_dict())
                # 如果端子排为空，则使用前一行的值
                if not terminal_info.terminal_block and terminal_blocks:
                    terminal_info.terminal_block = terminal_blocks[-1].terminal_block
                # 如果左侧右侧为空，则使用前一行的值
                if not terminal_info.side and terminal_blocks:
                    terminal_info.side = terminal_blocks[-1].side
                if not terminal_info.cabinet_name and terminal_blocks:
                    terminal_info.cabinet_name = terminal_blocks[-1].cabinet_name or cabinet_name
                terminal_blocks.append(terminal_info)
                successful_count += 1
            except Exception as e:
                error_count += 1
                print(f"处理第 {index + 1} 行数据时出错: {e}")
                print(f"问题数据: {row.to_dict()}")
                continue

        print(f"\n数据处理完成: 成功 {successful_count} 条, 失败 {error_count} 条")
        return terminal_blocks


# ============================================================================
# Converter: Legacy TerminalInfo to New Model
# ============================================================================

class LegacyConverter:
    """将旧的TerminalInfo数据转换为新的CabinetSystem模型"""
    
    @staticmethod
    def convert_to_cabinet_system(terminal_infos: List[TerminalInfo]) -> CabinetSystem:
        """
        将TerminalInfo列表转换为CabinetSystem
        
        Args:
            terminal_infos: TerminalInfo对象列表
            
        Returns:
            CabinetSystem对象
        """
        system = CabinetSystem()
        
        # 第一遍：创建机柜、端子排和端子
        for info in terminal_infos:
            cabinet_num = info.cabinet_name or "默认机柜"
            
            # 获取或创建机柜
            cabinet = system.get_cabinet(cabinet_num)
            if not cabinet:
                cabinet = Cabinet(number=cabinet_num)
                system.add_cabinet(cabinet)
            
            # 获取或创建端子排
            if info.terminal_block:
                terminal_block = cabinet.get_terminal_block(info.terminal_block)
                if not terminal_block:
                    terminal_block = TerminalBlock(
                        name=info.terminal_block,
                        description=info.terminal_block_desc
                    )
                    cabinet.add_terminal_block(terminal_block)
                
                # 创建端子
                terminal = Terminal(
                    name=info.terminal_number,
                    circuit_number=info.circuit_number if info.circuit_number else None,
                    cable_number=info.cable_number if info.cable_number else None
                )
                terminal_block.add_terminal(terminal)
        
        # 第二遍：创建连接关系
        for info in terminal_infos:
            if not info.terminal_block or not info.terminal_number:
                continue
            
            cabinet_num = info.cabinet_name or "默认机柜"
            from_ref = f"{cabinet_num}/{info.terminal_block}:{info.terminal_number}"
            
            # 处理互联端子（直连）
            for interconnect in info.interconnect_terminal:
                if not interconnect:
                    continue
                
                # 解析互联端子引用
                to_ref = LegacyConverter._parse_interconnect_ref(
                    interconnect, cabinet_num, info.terminal_block
                )
                
                if to_ref:
                    connection = Connection(
                        from_ref=from_ref,
                        to_ref=to_ref,
                        connection_type=ConnectionType.DIRECT,
                        description="直接互联"
                    )
                    system.add_connection(connection)
            
            # 处理内部配线
            for internal in info.internal_wiring:
                if not internal:
                    continue
                
                # 内部配线可能指向装置端子或其他端子
                to_ref = LegacyConverter._parse_interconnect_ref(
                    internal, cabinet_num, info.terminal_block
                )
                
                if to_ref:
                    connection = Connection(
                        from_ref=from_ref,
                        to_ref=to_ref,
                        connection_type=ConnectionType.INTERNAL_WIRE,
                        description="内部配线"
                    )
                    system.add_connection(connection)
            
            # 处理回路连接
            if info.circuit_number and info.cable_number:
                # 回路连接需要找到所有具有相同回路号和电缆编号的端子
                for other_info in terminal_infos:
                    if (other_info.circuit_number == info.circuit_number and
                        other_info.cable_number == info.cable_number and
                        other_info != info):
                        
                        other_cabinet = other_info.cabinet_name or "默认机柜"
                        if not other_info.terminal_block or not other_info.terminal_number:
                            continue
                        
                        to_ref = f"{other_cabinet}/{other_info.terminal_block}:{other_info.terminal_number}"
                        
                        # 避免重复添加双向连接
                        if from_ref < to_ref:  # 只添加一次
                            connection = Connection(
                                from_ref=from_ref,
                                to_ref=to_ref,
                                connection_type=ConnectionType.CIRCUIT,
                                circuit_number=info.circuit_number,
                                cable_number=info.cable_number,
                                description=f"回路{info.circuit_number}"
                            )
                            system.add_connection(connection)
        
        return system
    
    @staticmethod
    def _parse_interconnect_ref(ref: str, default_cabinet: str, default_block: str) -> str:
        """
        解析互联端子引用，补全默认机柜和端子排
        
        Args:
            ref: 端子引用字符串
            default_cabinet: 默认机柜编号
            default_block: 默认端子排名称
            
        Returns:
            完整的端子引用字符串
        """
        ref = (ref or "").strip()
        if not ref:
            return ""
        
        # 完整格式：机柜/端子排:端子号
        if "/" in ref and ":" in ref:
            return ref
        
        # 带端子排：端子排:端子号
        if ":" in ref:
            return f"{default_cabinet}/{ref}"
        
        # 仅端子号
        return f"{default_cabinet}/{default_block}:{ref}"


def export_to_excel(terminal_blocks: List[TerminalInfo], output_path: str):
    """导出数据到Excel文件"""
    try:
        data = []
        for terminal in terminal_blocks:
            data.append({
                '机柜名称': terminal.cabinet_name,
                '回路号': terminal.circuit_number,
                '端子排说明': terminal.terminal_block_desc,
                '端子排': terminal.terminal_block,
                '端子号': terminal.terminal_number,
                '左侧/右侧': terminal.side,
                '内部配线': ';'.join(terminal.internal_wiring),  # 列表转字符串
                '互联端子号': ';'.join(terminal.interconnect_terminal),  # 列表转字符串
                '功能说明': terminal.function_desc,
                '外部接线': terminal.external_wiring,
                '电缆芯编号': terminal.cable_core_number,
                '电缆编号': terminal.cable_number,
                '芯号': terminal.core_number,
                '电缆型号': terminal.cable_model,
                '对侧设备编号': terminal.opposite_device_number,
                '对侧设备名称': terminal.opposite_device_name,
                '备注': terminal.remarks,
                'COLWIRETExT': terminal.col_wire_text,
                '线缆型号': terminal.cable_type
            })
        
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        print(f"数据已导出到: {output_path}")
    except Exception as e:
        print(f"导出数据失败: {e}")

def print_terminal_info(terminal: TerminalInfo):
    """打印单个端子信息"""
    print(f"机柜名称: {terminal.cabinet_name}")
    print(f"回路号: {terminal.circuit_number}")
    print(f"端子排: {terminal.terminal_block}")
    print(f"端子号: {terminal.terminal_number}")
    print(f"位置: {terminal.side}")
    print(f"内部配线: {terminal.internal_wiring}")
    print(f"功能说明: {terminal.function_desc}")
    print(f"电缆编号: {terminal.cable_number}")
    print(f"对侧设备: {terminal.opposite_device_name}")
    print("-" * 50)

class ConnectionGraph:
    """
    将端子和回路建成无向图并能导出按机柜->端子排->端子分层的 draw.io XML。
    更新以支持新的CabinetSystem模型。
    """
    CIRCUIT_PREFIX = "@CIRCUIT:"
    INTERNAL_PREFIX = "@INTERNAL:"
    CONNECTION_PREFIX = "@CONN:"

    def __init__(self):
        # 邻接表：键为节点（tuple 或 circuit/internal/conn string），值为相邻节点集合
        self.adj: Dict[Any, Set[Any]] = defaultdict(set)
        # 记录所有终端节点对应的 TerminalInfo，键为三元组 (cabinet, block, terminal)
        self.terminal_info_map: Dict[tuple, TerminalInfo] = {}
        # 记录边集合，用 frozenset({a,b}) 保证无向边唯一（a/b 可以是 tuple 或 string）
        self.edges: Set[frozenset] = set()
        # 可选的边标签（frozenset({a,b}) -> str），用于标注来自回路表/柜内连接表的连接关系（如 开关/常闭开关）
        self.edge_labels: Dict[frozenset, str] = {}
        # 连接件计数（如果需要）
        self._conn_counter = 0
        # 新增：CabinetSystem引用（可选）
        self.cabinet_system: Optional[CabinetSystem] = None

    @staticmethod
    def make_terminal_node(cabinet: str, block: str, terminal: str) -> tuple:
        """返回端子节点三元组 (cabinet, block, terminal)，去除外部空白"""
        return ((cabinet or "").strip(), (block or "").strip(), (terminal or "").strip())

    @staticmethod
    def make_terminal_id_str(node: tuple) -> str:
        """把端子节点三元组格式化为可读字符串 'Cabinet/Block:Terminal'（仅用于显示）"""
        cab, blk, ter = node
        return f"{cab}/{blk}:{ter}"

    @staticmethod
    def make_circuit_node(circuit: str) -> str:
        circuit = (circuit or "").strip()
        return f"{ConnectionGraph.CIRCUIT_PREFIX}{circuit}"

    @staticmethod
    def make_internal_node(name: str) -> str:
        """把 internal wiring 名称包装为图中使用的字符串节点"""
        n = (name or "").strip()
        return f"{ConnectionGraph.INTERNAL_PREFIX}{n}"

    def make_connection_node(self, label: str, file_stem: Optional[str]=None, idx: Optional[int]=None) -> str:
        """创建唯一的 connection 节点字符串"""
        lab = (label or "").strip()
        # include file_stem and idx when available for determinism
        suf = ""
        if file_stem is not None and idx is not None:
            suf = f":{file_stem}:{idx}"
        else:
            suf = f":{self._conn_counter}"
            self._conn_counter += 1
        return f"{self.CONNECTION_PREFIX}{lab}{suf}"

    def _record_edge(self, a: Any, b: Any, label: Optional[str] = None):
        """内部：记录无向边为 frozenset，以保证唯一性；可附带边标签（不一定覆盖已有回路标签）"""
        if a is None or b is None:
            return
        if a == "" or b == "":
            return
        key = frozenset({a, b})
        self.edges.add(key)
        if label and label.strip():
            self.edge_labels[key] = label.strip()

    def add_edge(self, a: Any, b: Any, label: Optional[str] = None):
        """在邻接表中加入无向边并记录到 edges，支持可选边标签"""
        if not a or not b:
            return
        self.adj[a].add(b)
        self.adj[b].add(a)
        self._record_edge(a, b, label)

    def _parse_interconnect(self, inter: str, default_cab: str, default_blk: str) -> Optional[Any]:
        """
        将互联端子字符串解析为节点：
          支持格式：
            - 完整： "Cabinet/Block:Terminal"
            - 带端子排 "Block:Terminal"（使用默认机柜）
            - 仅端子号 "Terminal"（使用默认机柜和端子排）
        返回节点（三元组）或 None（解析失败）。
        """
        s = (inter or "").strip()
        if not s:
            return None
        if ":" in s:
            left, right = s.split(":", 1)
            left = left.strip()
            right = right.strip()
            if "/" in left:
                cab, blk = left.split("/", 1)
                return self.make_terminal_node(cab.strip(), blk.strip(), right)
            else:
                return self.make_terminal_node(default_cab or "", left, right)
        else:
            # 仅端子号
            return self.make_terminal_node(default_cab or "", default_blk or "", s)

    def add_terminal(self, terminal: TerminalInfo):
        node = self.make_terminal_node(terminal.cabinet_name, terminal.terminal_block, terminal.terminal_number)
        self.terminal_info_map[node] = terminal
        # ensure node exists in adj
        _ = self.adj[node]

        # 连接到回路节点（如果有回路号）——保留回路节点以便查询，但导出 drawio 时不把回路节点作为图元绘制
        if terminal.circuit_number:
            cnode = self.make_circuit_node(terminal.circuit_number)
            self.add_edge(node, cnode)

        # 处理互联端子（互联端子可能只写端子号，也可能写端子排:端子 或 完整路径）
        for inter in terminal.interconnect_terminal:
            parsed = self._parse_interconnect(inter, terminal.cabinet_name, terminal.terminal_block)
            if parsed:
                self.add_edge(node, parsed)

        # 处理 internal_wiring：始终以完整名称（带前缀字符串）保存 internal 节点，不拼接默认柜/端子排
        for internal in terminal.internal_wiring:
            if not internal:
                continue
            inode = self.make_internal_node(internal)
            self.add_edge(node, inode)
            # 若存在真实端子 terminal_number 与 internal 相等，则把 internal 节点与该端子连边
            for real_node in list(self.terminal_info_map.keys()):
                try:
                    if isinstance(real_node, tuple) and real_node[2] == internal:
                        self.add_edge(inode, real_node)
                except Exception:
                    continue

        return node

    def build_from_terminals(self, terminals: Iterable[TerminalInfo]):
        # 清空已有图
        self.adj.clear()
        self.terminal_info_map.clear()
        self.edges.clear()
        self.edge_labels.clear()
        self._conn_counter = 0
        # 先加入所有端子节点（以便互联引用不存在时也能查询到节点）
        for t in terminals:
            node = self.make_terminal_node(t.cabinet_name, t.terminal_block, t.terminal_number)
            self.terminal_info_map[node] = t
            _ = self.adj[node]

        # 再添加实际边
        for t in terminals:
            self.add_terminal(t)
    
    def build_from_cabinet_system(self, system: CabinetSystem):
        """
        从CabinetSystem构建连接图
        
        Args:
            system: CabinetSystem对象
        """
        # 清空已有图
        self.adj.clear()
        self.terminal_info_map.clear()
        self.edges.clear()
        self.edge_labels.clear()
        self._conn_counter = 0
        self.cabinet_system = system
        
        # 添加所有端子节点
        for cabinet in system.cabinets.values():
            # 添加端子排的端子
            for terminal_block in cabinet.terminal_blocks.values():
                for terminal in terminal_block.terminals:
                    node = self.make_terminal_node(
                        cabinet.number,
                        terminal_block.name,
                        terminal.name
                    )
                    # 创建一个虚拟的TerminalInfo用于向后兼容
                    info = TerminalInfo(
                        cabinet_name=cabinet.number,
                        circuit_number=terminal.circuit_number or "",
                        terminal_block_desc=terminal_block.description,
                        terminal_block=terminal_block.name,
                        terminal_number=terminal.name,
                        side="",
                        internal_wiring=[],
                        interconnect_terminal=[],
                        function_desc="",
                        external_wiring="",
                        cable_core_number="",
                        cable_number=terminal.cable_number or "",
                        core_number="",
                        cable_model="",
                        opposite_device_number="",
                        opposite_device_name="",
                        remarks="",
                        col_wire_text="",
                        cable_type=""
                    )
                    self.terminal_info_map[node] = info
                    _ = self.adj[node]
                    
                    # 添加回路节点连接
                    if terminal.circuit_number:
                        cnode = self.make_circuit_node(terminal.circuit_number)
                        self.add_edge(node, cnode)
            
            # 添加装置端子节点
            for device in cabinet.devices.values():
                for terminal in device.terminals:
                    # 装置端子使用特殊格式：机柜/装置/端子名
                    node = self.make_terminal_node(
                        cabinet.number,
                        f"DEV_{device.name}",
                        terminal.name
                    )
                    info = TerminalInfo(
                        cabinet_name=cabinet.number,
                        circuit_number="",
                        terminal_block_desc=device.description,
                        terminal_block=f"DEV_{device.name}",
                        terminal_number=terminal.name,
                        side="",
                        internal_wiring=[],
                        interconnect_terminal=[],
                        function_desc="",
                        external_wiring="",
                        cable_core_number="",
                        cable_number="",
                        core_number="",
                        cable_model="",
                        opposite_device_number="",
                        opposite_device_name="",
                        remarks="",
                        col_wire_text="",
                        cable_type=""
                    )
                    self.terminal_info_map[node] = info
                    _ = self.adj[node]
            
            # 添加元件端子节点
            for component in cabinet.components.values():
                for terminal in component.terminals:
                    node = self.make_terminal_node(
                        cabinet.number,
                        component.name,
                        terminal.name
                    )
                    info = TerminalInfo(
                        cabinet_name=cabinet.number,
                        circuit_number="",
                        terminal_block_desc=component.description,
                        terminal_block=component.name,
                        terminal_number=terminal.name,
                        side="",
                        internal_wiring=[],
                        interconnect_terminal=[],
                        function_desc="",
                        external_wiring="",
                        cable_core_number="",
                        cable_number="",
                        core_number="",
                        cable_model="",
                        opposite_device_number="",
                        opposite_device_name="",
                        remarks="",
                        col_wire_text="",
                        cable_type=""
                    )
                    self.terminal_info_map[node] = info
                    _ = self.adj[node]
                
                # 添加元件内部连接
                for term1, term2 in component.internal_connections:
                    node1 = self.make_terminal_node(cabinet.number, component.name, term1)
                    node2 = self.make_terminal_node(cabinet.number, component.name, term2)
                    self.add_edge(node1, node2, label=f"{component.component_type.value}")
        
        # 添加连接边
        for connection in system.connections:
            # 解析源和目标端子引用
            from_parsed = system.parse_terminal_ref(connection.from_ref)
            to_parsed = system.parse_terminal_ref(connection.to_ref)
            
            if not from_parsed or not to_parsed:
                continue
            
            from_cabinet, from_type, from_container, from_terminal = from_parsed
            to_cabinet, to_type, to_container, to_terminal = to_parsed
            
            # 构建节点
            if from_type == "device":
                from_node = self.make_terminal_node(from_cabinet, f"DEV_{from_terminal}", from_terminal)
            else:
                from_node = self.make_terminal_node(from_cabinet, from_container, from_terminal)
            
            if to_type == "device":
                to_node = self.make_terminal_node(to_cabinet, f"DEV_{to_terminal}", to_terminal)
            else:
                to_node = self.make_terminal_node(to_cabinet, to_container, to_terminal)
            
            # 根据连接类型添加边
            if connection.connection_type == ConnectionType.THROUGH_COMPONENT:
                # 通过元件连接，需要创建中间节点
                if connection.component_name:
                    conn_node = self.make_connection_node(connection.component_name)
                    _ = self.adj[conn_node]
                    self.add_edge(from_node, conn_node, label=connection.description)
                    self.add_edge(conn_node, to_node, label=connection.description)
            else:
                # 直接连接
                label = connection.description
                if connection.circuit_number:
                    label = f"{connection.circuit_number}"
                self.add_edge(from_node, to_node, label=label)

    def build_from_terminals(self, terminals: Iterable[TerminalInfo]):
        # 清空已有图
        self.adj.clear()
        self.terminal_info_map.clear()
        self.edges.clear()
        self.edge_labels.clear()
        self._conn_counter = 0
        # 先加入所有端子节点（以便互联引用不存在时也能查询到节点）
        for t in terminals:
            node = self.make_terminal_node(t.cabinet_name, t.terminal_block, t.terminal_number)
            self.terminal_info_map[node] = t
            _ = self.adj[node]

        # 再添加实际边
        for t in terminals:
            self.add_terminal(t)

    
    def export_system_to_drawio(self, output_dir: Path, separate_by_cabinet: bool = True):
        """
        从CabinetSystem导出drawio文件
        
        Args:
            output_dir: 输出目录
            separate_by_cabinet: 是否为每个机柜生成单独的文件
        """
        if not self.cabinet_system:
            raise ValueError("未设置CabinetSystem，请先调用build_from_cabinet_system")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if separate_by_cabinet:
            # 为每个机柜生成单独的图纸
            for cabinet in self.cabinet_system.cabinets.values():
                # 找到包含该机柜端子的所有组件
                comps = self.get_components_by_cabinet(cabinet.number)
                
                for rep, comp in comps.items():
                    # 生成文件名
                    safe_rep = rep.replace("/", "_").replace(":", "_")
                    safe_cabinet = cabinet.number.replace("/", "_")
                    filename = output_dir / f"cabinet_{safe_cabinet}_{safe_rep}.drawio"
                    
                    try:
                        self.export_drawio_xml(comp, filename, title=f"{cabinet.number} - {rep}")
                        print(f"已导出: {filename}")
                    except Exception as e:
                        print(f"导出失败 {filename}: {e}")
        else:
            # 导出所有组件到单独的文件
            comps = self.get_all_components()
            for rep, comp in comps.items():
                filename = output_dir / make_filename_for_component(comp, self)
                try:
                    self.export_drawio_xml(comp, filename, title=rep)
                    print(f"已导出: {filename}")
                except Exception as e:
                    print(f"导出失败 {filename}: {e}")

    def bfs_component(self, start: Any) -> Set[Any]:
        if start not in self.adj:
            return set()
        seen = set([start])
        q = deque([start])
        while q:
            u = q.popleft()
            for v in self.adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        return seen

    def get_component_by_terminal(self, cabinet: str, block: str, terminal: str) -> Set[Any]:
        node = self.make_terminal_node(cabinet, block, terminal)
        return self.bfs_component(node)

    def get_component_by_terminal_full(self, full_terminal: str) -> Set[Any]:
        parsed = self._parse_interconnect(full_terminal, None, None)
        if parsed is None:
            return set()
        return self.bfs_component(parsed)

    def get_component_by_circuit(self, circuit: str) -> Set[Any]:
        cnode = self.make_circuit_node(circuit)
        return self.bfs_component(cnode)

    def _node_sort_key(self, node: Any) -> str:
        """用于选择稳定代表键的排序键（字符串形式）"""
        if isinstance(node, tuple):
            return f"T:{node[0]}|{node[1]}|{node[2]}"
        return f"{node}"

    def get_all_components(self) -> Dict[str, Set[Any]]:
        """返回以任意代表节点字符串为键的连通分量字典（所有分量）"""
        visited = set()
        components: Dict[str, Set[Any]] = {}
        for node in list(self.adj.keys()):
            if node in visited:
                continue
            comp = self.bfs_component(node)
            visited.update(comp)
            rep_node = min(comp, key=self._node_sort_key) if comp else node
            rep_key = self.make_terminal_id_str(rep_node) if isinstance(rep_node, tuple) else rep_node
            components[rep_key] = comp
        return components

    def get_components_by_cabinet(self, cabinet: str) -> Dict[str, Set[Any]]:
        """返回包含该机柜中任一端子的所有连通分量"""
        comps = self.get_all_components()
        res: Dict[str, Set[Any]] = {}
        for rep, comp in comps.items():
            for node in comp:
                if isinstance(node, tuple) and node[0] == cabinet:
                    res[rep] = comp
                    break
        return res

    def get_components_by_terminal_block(self, cabinet: str, block: str) -> Dict[str, Set[Any]]:
        comps = self.get_all_components()
        res: Dict[str, Set[Any]] = {}
        for rep, comp in comps.items():
            if any(isinstance(n, tuple) and n[0] == cabinet and n[1] == block for n in comp):
                res[rep] = comp
        return res

    def get_component_subgraph_adj(self, comp: Set[Any]) -> Dict[str, Set[str]]:
        """返回子图的邻接表（只包含 comp 中的节点与内部边），以可读字符串作为键和值"""
        def fmt(n: Any) -> str:
            return self.make_terminal_id_str(n) if isinstance(n, tuple) else n

        sub_adj: Dict[str, Set[str]] = {}
        for n in comp:
            neigh = self.adj.get(n, set())
            sub_adj[fmt(n)] = set(fmt(x) for x in neigh if x in comp)
        return sub_adj

    def get_component_edges(self, comp: Set[Any]) -> list:
        """返回子图的边列表（每条边为 (a, b)，均为可读字符串）"""
        res = []
        for edge in self.edges:
            if len(edge) != 2:
                continue
            a, b = tuple(edge)
            if a in comp and b in comp:
                a_str = self.make_terminal_id_str(a) if isinstance(a, tuple) else a
                b_str = self.make_terminal_id_str(b) if isinstance(b, tuple) else b
                res.append((a_str, b_str))
        return res

    def summarize_component(self, comp: Set[Any]) -> Dict[str, Any]:
        """把组件转成可序列化的摘要结构，包含节点和边信息（用于拓扑绘制）"""
        terminals = [n for n in comp if isinstance(n, tuple)]
        circuits = [n[len(self.CIRCUIT_PREFIX):] for n in comp if isinstance(n, str) and n.startswith(self.CIRCUIT_PREFIX)]
        internals_set = set()
        for n in comp:
            if isinstance(n, str) and not n.startswith(self.CIRCUIT_PREFIX):
                if n.startswith(self.INTERNAL_PREFIX):
                    internals_set.add(n[len(self.INTERNAL_PREFIX):])
                elif n.startswith(self.CONNECTION_PREFIX):
                    # connection 节点将其显示 label 提取
                    core = n[len(self.CONNECTION_PREFIX):]
                    internals_set.add(core.split(":", 1)[0] if ":" in core else core)
                else:
                    internals_set.add(n)
        for t in terminals:
            info = self.terminal_info_map.get(t)
            if info:
                for name in info.internal_wiring:
                    if name:
                        internals_set.add(name)
        internals = sorted(internals_set)
        edges = self.get_component_edges(comp)
        adj = self.get_component_subgraph_adj(comp)
        terminal_infos = {self.make_terminal_id_str(n): self.terminal_info_map.get(n) for n in terminals}
        return {
            "terminals": sorted([self.make_terminal_id_str(n) for n in terminals]),
            "circuits": sorted(circuits),
            "internals": internals,
            "size": len(comp),
            "edges": edges,
            "adj": adj,
            "terminal_infos": terminal_infos
        }

    def _layout_by_cabinet_block(self, terminals: Iterable[tuple],
                                 term_w:int=80, term_h:int=28,
                                 hgap:int=10, vgap:int=8,
                                 max_cols:int=8,
                                 block_padding:int=8, cabinet_padding:int=16,
                                 block_title_h:int=20):
        """
        根据机柜/端子排组织端子并返回每个终端的全局位置以及容器尺寸：
          返回 dict:
            positions: node -> (x,y,w,h)
            cabinet_boxes: cab -> (x,y,w,h, id_placeholder)
            block_boxes: (cab,blk) -> (x,y,w,h, id_placeholder)
        """
        from math import ceil

        # 组织结构
        cabinets = defaultdict(lambda: defaultdict(list))  # cab -> blk -> [nodes]
        for n in terminals:
            cab, blk, ter = n
            cabinets[cab][blk].append(n)

        # 计算尺寸
        positions = {}
        cabinet_boxes = {}
        block_boxes = {}

        start_x = 40
        x = start_x
        for cab in sorted(cabinets.keys()):
            blocks = cabinets[cab]
            # 先测量每个 block 的尺寸
            block_dims = {}
            for blk, nodes in blocks.items():
                cnt = len(nodes)
                cols = min(max_cols, cnt) if cnt>0 else 1
                rows = ceil(cnt/cols) if cnt>0 else 1
                bw = cols * term_w + (cols-1)*hgap + 2*block_padding
                bh = block_title_h + rows*term_h + (rows-1)*vgap + 2*block_padding
                block_dims[blk] = (cols, rows, bw, bh)
            # cabinet 尺寸基于最大的 block 宽度与 blocks 垂直堆叠高度
            max_block_w = max((d[2] for d in block_dims.values()), default=(term_w + 2*block_padding))
            total_h = sum((d[3] for d in block_dims.values()))
            inter_block_gap = vgap
            cab_w = max_block_w + 2*cabinet_padding
            cab_h = total_h + (len(block_dims)-1)*inter_block_gap + 2*cabinet_padding
            cab_x = x
            cab_y = 40
            cabinet_boxes[cab] = (cab_x, cab_y, cab_w, cab_h)
            # place blocks stacked from top inside cabinet
            by = cab_y + cabinet_padding
            for blk in sorted(blocks.keys()):
                cols, rows, bw, bh = block_dims[blk]
                blk_x = cab_x + cabinet_padding + (max_block_w - bw)/2
                blk_y = by
                block_boxes[(cab, blk)] = (blk_x, blk_y, bw, bh)
                # place terminal nodes in grid
                nodes = sorted(blocks[blk], key=self._node_sort_key)
                for idx, node in enumerate(nodes):
                    col = idx % cols
                    row = idx // cols
                    tx = blk_x + block_padding + col * (term_w + hgap)
                    ty = blk_y + block_title_h + block_padding + row * (term_h + vgap)
                    positions[node] = (tx, ty, term_w, term_h)
                by += bh + inter_block_gap
            # advance cabinet x
            x += cab_w + 80

        return positions, cabinet_boxes, block_boxes

    def _layout_terminals_grid(self, terminals: Iterable[tuple],
                               term_w:int=120, term_h:int=48,
                               hgap:int=60, vgap:int=20,
                               max_cols:int=8):
        """
        新布局：
          - 同一 (cabinet, block) 的端子纵向堆叠在一起（每个 block 为一列）。
          - 端子排(block)之间的相对顺序由 block-level 的连通关系决定：把 block 看作图的节点，
            根据 block 间的连接关系做 BFS 分层，按层分配横向位置，相同层内纵向排列不同 block。
          - 每个 block 内端子按 try_chain_order（链式互联）或自然序排序，纵向排列。
        返回 positions dict: node -> (x,y,w,h)
        """
        from math import ceil

        terms = list(sorted(list(terminals), key=self._node_sort_key))
        if not terms:
            return {}

        # 分组： (cab, blk) -> [nodes]
        blocks = defaultdict(list)
        for n in terms:
            cab, blk, ter = n
            blocks[(cab, blk)].append(n)

        # 构建 block-level 邻接：若有端子间直接边或属于同一回路则视为 block 间相连
        block_adj: Dict[tuple, Set[tuple]] = defaultdict(set)
        # 直接互联/边
        term_set = set(terms)
        for e in self.edges:
            if len(e) != 2:
                continue
            a, b = tuple(e)
            if not (isinstance(a, tuple) and isinstance(b, tuple)):
                continue
            if a not in term_set or b not in term_set:
                continue
            ba = (a[0], a[1])
            bb = (b[0], b[1])
            if ba != bb:
                block_adj[ba].add(bb)
                block_adj[bb].add(ba)

        # 回路关联也作为 block 之间的连接（同一回路的端子所在 block 互连）
        circuits = defaultdict(list)
        for node in terms:
            info = self.terminal_info_map.get(node)
            if info and info.circuit_number:
                circuits[info.circuit_number].append(node)
        for circ_nodes in circuits.values():
            blocks_in_circ = set((n[0], n[1]) for n in circ_nodes)
            blist = list(blocks_in_circ)
            for i in range(len(blist)):
                for j in range(i+1, len(blist)):
                    a = blist[i]; b = blist[j]
                    if a != b:
                        block_adj[a].add(b)
                        block_adj[b].add(a)

        # BFS 给 block 分层，起点选第一个 block（若有未访问 block，依次再 BFS）
        layer_of: Dict[tuple, int] = {}
        q = deque()
        all_blocks = list(blocks.keys())
        if not all_blocks:
            return {}
        start = all_blocks[0]
        layer_of[start] = 0
        q.append(start)
        while q:
            cur = q.popleft()
            for nb in block_adj.get(cur, set()):
                if nb not in layer_of:
                    layer_of[nb] = layer_of[cur] + 1
                    q.append(nb)
        # 未访问的 block 分配后续层
        next_layer = max(layer_of.values()) + 1 if layer_of else 0
        for b in all_blocks:
            if b not in layer_of:
                layer_of[b] = next_layer
                next_layer += 1

        # 为每个 block 内的端子确定顺序（尽量恢复链式顺序）
        def try_chain_order(nodes: List[tuple]) -> List[tuple]:
            if not nodes:
                return []
            nodes_set = set(nodes)
            local_adj = {n: set() for n in nodes}
            for n in nodes:
                for nb in self.adj.get(n, set()):
                    if isinstance(nb, tuple) and nb in nodes_set:
                        local_adj[n].add(nb)
            degs = {n: len(local_adj[n]) for n in nodes}
            if any(d > 2 for d in degs.values()):
                return []
            endpoints = [n for n, d in degs.items() if d == 1]
            startn = endpoints[0] if endpoints else nodes[0]
            order = []
            cur = startn
            while cur is not None:
                order.append(cur)
                nexts = [m for m in local_adj[cur] if m not in order]
                if nexts:
                    cur = nexts[0]
                else:
                    cur = None
            if len(order) == len(nodes):
                return order
            return []

        def natural_key(node: tuple):
            ter = node[2]
            m = re.search(r'(\d+)', ter)
            if m:
                return (int(m.group(1)), ter)
            return (10**9, ter, node[0], node[1])

        # 计算每层的 blocks 并布局：横向按层，纵向按 block 列排列
        layers: Dict[int, List[tuple]] = defaultdict(list)
        for b, l in layer_of.items():
            layers[l].append(b)
        # 排序层内 blocks 稳定性
        for l in layers:
            layers[l].sort(key=lambda b: (b[0] or "", b[1] or ""))

        positions: Dict[tuple, tuple] = {}
        start_x = 40
        start_y = 40
        layer_gap_x = term_w + 3 * hgap
        block_gap_y = 40

        # 先测算每 block 的高度以便纵向排列
        block_sizes: Dict[tuple, tuple] = {}
        for b, nodes in blocks.items():
            # 节点顺序
            chain = try_chain_order(nodes)
            if chain:
                ordered = chain
            else:
                ordered = sorted(nodes, key=lambda n: (natural_key(n), self._node_sort_key(n)))
            rows = len(ordered)
            bw = term_w
            bh = rows * term_h + max(0, rows-1) * vgap
            block_sizes[b] = (ordered, bw, bh)

        # 对每层分配横坐标并在该层内纵向排列 blocks
        for layer_idx in sorted(layers.keys()):
            bx = start_x + layer_idx * layer_gap_x
            # 计算这一层总高度，方便从 top 开始居中或按 start_y 排列；这里用从 start_y 开始顺序排列
            y = start_y
            for b in layers[layer_idx]:
                ordered, bw, bh = block_sizes.get(b, ([], term_w, term_h))
                # 为该 block 中的每个终端纵向放置
                for idx, node in enumerate(ordered):
                    tx = bx
                    ty = y + idx * (term_h + vgap)
                    positions[node] = (tx, ty, term_w, term_h)
                # advance y 为下一个 block 留出高度 + gap
                y += bh + block_gap_y

        return positions

    def load_connection_sheets(self, dir_path: str):
        """
        读取回路表并把连接加入图中。若存在 '连接关系' 字段，则以 connection 节点（@CONN:label:...）作为中间元件连接两端。
        名称若无法解析为真实三元组，会作为全局 internal 名称字符串节点保存（不拼接默认 cabinet/block）。
        """
        p = Path(dir_path)
        if not p.exists():
            print(f"连接表目录不存在: {dir_path}")
            return

        def resolve_name_to_nodes(name: str) -> List[Any]:
            name = (name or "").strip()
            if not name:
                return []
            # 若包含 ':' 或 '/' 尝试解析为三元组并精确匹配真实端子
            if ":" in name or "/" in name:
                parsed = self._parse_interconnect(name, None, None)
                if parsed:
                    cab_p, blk_p, ter_p = parsed
                    res = []
                    for node in self.terminal_info_map.keys():
                        match = True
                        if ter_p and node[2] != ter_p:
                            match = False
                        if cab_p and cab_p != "" and node[0] != cab_p:
                            match = False
                        if blk_p and blk_p != "" and node[1] != blk_p:
                            match = False
                        if match:
                            res.append(node)
                    if res:
                        return res
                    # 未找到真实端子 -> 返回作为 internal 字符串节点
                    inode = self.make_internal_node(name)
                    _ = self.adj[inode]
                    return [inode]
                else:
                    return []
            # 仅端子号：全局匹配 terminal_number 字段
            matches = [n for n in self.terminal_info_map.keys() if n[2] == name]
            if matches:
                return matches
            # 未匹配 -> 作为 internal 名称字符串节点
            inode = self.make_internal_node(name)
            _ = self.adj[inode]
            return [inode]

        def split_multi(value: str) -> List[str]:
            if not value:
                return []
            parts = re.split(r'[;,，；/]+', value)
            return [p.strip() for p in parts if p.strip()]

        for file in sorted(p.rglob("*.xlsx")):
            if file.name.startswith("~$"):
                continue
            try:
                xls = pd.ExcelFile(file)
            except Exception as e:
                print(f"无法打开 Excel 文件 {file}: {e}")
                continue
            for sheet in xls.sheet_names:
                if "柜内端子连接" not in sheet:
                    continue
                try:
                    df = pd.read_excel(xls, sheet_name=sheet)
                except Exception as e:
                    print(f"读取表 {file} - {sheet} 失败: {e}")
                    continue
                df.columns = [str(c).strip() for c in df.columns]
                def find_col(possible: List[str]) -> Optional[str]:
                    for cand in possible:
                        for c in df.columns:
                            if cand in c:
                                return c
                    return None

                col_term = find_col(["端子号", "端子", "端子编号"])
                col_inter = find_col(["互联端子号", "互联端子", "互联"])
                col_relation = find_col(["连接关系", "关系", "连接类型"])

                if not col_term or not col_inter:
                    print(f"表 {file}:{sheet} 未找到必需列 '端子号' 或 '互联端子号'，跳过")
                    continue

                for idx, row in df.iterrows():
                    left_raw = str(row.get(col_term, "") or "").strip()
                    right_raw = str(row.get(col_inter, "") or "").strip()
                    relation = str(row.get(col_relation, "") or "").strip() if col_relation else ""

                    left_names = split_multi(left_raw)
                    right_names = split_multi(right_raw)
                    if not left_names or not right_names:
                        continue

                    left_nodes = []
                    for ln in left_names:
                        left_nodes.extend(resolve_name_to_nodes(ln))
                    right_nodes = []
                    for rn in right_names:
                        right_nodes.extend(resolve_name_to_nodes(rn))

                    if not left_nodes or not right_nodes:
                        print(f"在 {file}:{sheet} 第 {idx+1} 行未解析到端子节点: 左 {left_raw} -> {left_nodes}, 右 {right_raw} -> {right_nodes}")
                        continue

                    for a in left_nodes:
                        for b in right_nodes:
                            if a == b:
                                continue
                            if relation:
                                conn_label = relation.strip()
                                conn_node = self.make_connection_node(conn_label, file.stem, idx)
                                _ = self.adj[conn_node]
                                self.add_edge(a, conn_node)
                                self.add_edge(conn_node, b)
                            else:
                                self.add_edge(a, b)
                print(f"已处理连接表: {file} - {sheet}")

    def export_drawio_xml(self, comp: Set[Any], output_path: Path, title: str = "diagram"):
        """
        导出 drawio XML。string 节点包括 INTERNAL_PREFIX 与 CONNECTION_PREFIX（回路节点除外）。
        """
        if not comp:
            raise ValueError("组件为空，无法导出 drawio。")

        draw_nodes = [n for n in comp if not (isinstance(n, str) and n.startswith(self.CIRCUIT_PREFIX))]
        if not draw_nodes:
            raise ValueError("组件中无可绘制节点。")

        layout_terms = []
        layout_map: Dict[Any, tuple] = {}
        for n in draw_nodes:
            if isinstance(n, tuple):
                layout_map[n] = n
                layout_terms.append(n)
            else:
                name = n
                if name.startswith(self.INTERNAL_PREFIX):
                    name = name[len(self.INTERNAL_PREFIX):]
                    synthetic = ("", name, "")
                elif name.startswith(self.CONNECTION_PREFIX):
                    core = name[len(self.CONNECTION_PREFIX):]
                    display_label = core.split(":", 1)[0] if ":" in core else core
                    synthetic = ("", display_label, "")
                else:
                    synthetic = ("", name, "")
                layout_map[n] = synthetic
                layout_terms.append(synthetic)

        # 调整间距以减少横向拉长；后续会把 connection 节点定位到它们连线端点的中点
        positions = self._layout_terminals_grid(layout_terms, term_w=120, term_h=48, hgap=30, vgap=12, max_cols=8)

        # 基于 layout_map 生成每个原始节点的最终位置（node_positions），
        # 并把 connection 节点放在其邻居的几何中心处，避免被挤到最右侧。
        node_positions: Dict[Any, tuple] = {}
        # 先填充基准位置（从 layout 结果或默认）
        for n in draw_nodes:
            ln = layout_map.get(n)
            base = positions.get(ln, (40, 40, 120, 48))
            # terminal 三元组通常使用默认大小；string 节点用同样默认，connection 节点会被覆盖
            node_positions[n] = tuple(base)

        # 将 connection 节点定位到其邻居中心位置（若有邻居）
        for n in draw_nodes:
            if isinstance(n, str) and n.startswith(self.CONNECTION_PREFIX):
                neigh = [x for x in self.adj.get(n, set()) if x in draw_nodes]
                if neigh:
                    centers = []
                    for m in neigh:
                        mx, my, mw, mh = node_positions.get(m, positions.get(layout_map.get(m), (40,40,120,48)))
                        centers.append((mx + mw/2.0, my + mh/2.0))
                    # 计算几何中心
                    cx = sum(p[0] for p in centers) / len(centers)
                    cy = sum(p[1] for p in centers) / len(centers)
                    # connection 元件尺寸与 draw.io 库一致
                    cw, ch = (75, 20)
                    nx = max(10, cx - cw/2.0)
                    ny = max(10, cy - ch/2.0)
                    node_positions[n] = (nx, ny, cw, ch)
                else:
                    # 没有邻居时使用默认位置（已存在）
                    pass

        id_map: Dict[Any, str] = {}
        next_id = 2
        def nid():
            nonlocal next_id
            v = str(next_id)
            next_id += 1
            return v

        cells = []
        cells.append('<mxCell id="0"/>')
        cells.append('<mxCell id="1" parent="0"/>')

        for node in sorted(draw_nodes, key=self._node_sort_key):
            cell_id = nid()
            id_map[node] = cell_id
            layout_node = layout_map.get(node)
            if isinstance(node, str):
                lab = node
                # connection 节点使用去前缀后的短 label（不含唯一后缀）
                if lab.startswith(self.CONNECTION_PREFIX):
                    core = lab[len(self.CONNECTION_PREFIX):]
                    lab = core.split(":", 1)[0] if ":" in core else core
                elif lab.startswith(self.INTERNAL_PREFIX):
                    lab = lab[len(self.INTERNAL_PREFIX):]
                label = escape(lab)
            else:
                label = escape(self.make_terminal_id_str(layout_node))
            # 使用预先计算的 node_positions（connection 节点已被居中）
            x, y, w, h = node_positions.get(node, positions.get(layout_node, (40, 40, 120, 48)))
            if isinstance(node, str) and node.startswith(self.CONNECTION_PREFIX):
                # 使用 draw.io 官方库的开关元件（singleSwitch），根据关系名选择 on/off
                # 不在元件内部显示文本（value 置空），通过 elSwitchState 控制外观
                core = node[len(self.CONNECTION_PREFIX):]
                rel = core.split(":", 1)[0] if ":" in core else core
                rel_l = (rel or "").lower()
                # 简单映射：包含 "常闭" 的关系使用 off，否则使用 on
                state = "off" if "常闭" in rel or "nc" in rel_l else "on"
                style = f"html=1;shape=mxgraph.electrical.electro-mechanical.singleSwitch;aspect=fixed;elSwitchState={state};"
                # node_positions 已设定尺寸
                # 元件不直接显示 label 文本（位置有限），使用空值
                cells.append(f'<mxCell id="{cell_id}" value="" style="{style}" vertex="1" parent="1">')
                cells.append(f'  <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>')
                cells.append('</mxCell>')
            else:
                style = "shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000"
                cells.append(f'<mxCell id="{cell_id}" value="{label}" style="{style}" vertex="1" parent="1">')
                cells.append(f'  <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>')
                cells.append('</mxCell>')

        edges_to_draw = {}
        for e in self.edges:
            if len(e) != 2:
                continue
            a, b = tuple(e)
            if a not in draw_nodes or b not in draw_nodes:
                continue
            key = tuple(sorted([a, b], key=self._node_sort_key))
            label = ""
            ai = self.terminal_info_map.get(a) if isinstance(a, tuple) else None
            bi = self.terminal_info_map.get(b) if isinstance(b, tuple) else None
            if ai and bi and ai.circuit_number and ai.circuit_number == bi.circuit_number:
                label = ai.circuit_number
            if not label:
                edge_key = frozenset({a, b})
                if edge_key in self.edge_labels:
                    label = self.edge_labels[edge_key]
            if key in edges_to_draw and edges_to_draw[key]:
                continue
            edges_to_draw[key] = label

        circuits = defaultdict(list)
        for node in draw_nodes:
            info = self.terminal_info_map.get(node) if isinstance(node, tuple) else None
            if info and info.circuit_number:
                circuits[info.circuit_number].append(node)

        for circ, nodes in circuits.items():
            if len(nodes) < 2:
                continue
            nodes_sorted = sorted(nodes, key=self._node_sort_key)
            for i in range(len(nodes_sorted)):
                for j in range(i+1, len(nodes_sorted)):
                    a = nodes_sorted[i]
                    b = nodes_sorted[j]
                    key = tuple(sorted([a, b], key=self._node_sort_key))
                    edges_to_draw[key] = circ

        for (a, b), label in edges_to_draw.items():
            src = id_map.get(a)
            tgt = id_map.get(b)
            if not src or not tgt:
                continue
            eid = nid()
            val = escape(label) if label else ""
            style = "edgeStyle=elbowEdgeStyle;edgeRadius=0;rounded=0;html=1;strokeColor=#000000;startArrow=none;endArrow=none"
            cells.append(f'<mxCell id="{eid}" value="{val}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">')
            cells.append('  <mxGeometry relative="1" as="geometry"/>')
            cells.append('</mxCell>')

        mxroot = "<root>\n" + "\n".join(cells) + "\n</root>"
        mxgraph = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<mxfile host="app.diagrams.net" modified="" agent="python" etag="">\n'
            f'  <diagram name="{escape(title)}" id="diagram1">\n'
            f'    <mxGraphModel dx="1420" dy="768" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169">\n'
            f'      {mxroot}\n'
            f'    </mxGraphModel>\n'
            f'  </diagram>\n'
            f'</mxfile>\n'
        )

        os.makedirs(output_path.parent, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(mxgraph)
        print(f"已导出 drawio XML 到: {output_path}")

def make_filename_for_component(comp, graph, prefix="component", ext="drawio"):
    """
    Compose an export filename that includes all circuit numbers present in the component.
    Circuits are sorted and joined by underscore. If no circuits, use 'no_circuit'.
    """
    summary = graph.summarize_component(comp)
    circuits = summary.get("circuits", [])
    if circuits:
        circuits_part = "_".join(sorted(circuits))
    else:
        circuits_part = "no_circuit"
    filename = f"{prefix}_circuits_{circuits_part}.{ext}"
    return filename

# 使用示例（保留原有入口，仅供快速测试）
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="读取端子排信息并构建连接图。")
    parser.add_argument("--term", type=str, help="包含端子排 Excel 文件的目录路径")
    parser.add_argument("--loop", type=str, help="包含回路表 Excel 文件的目录路径")
    parser.add_argument("--output_dir_path", type=str, default="outputs", help="输出 drawio 文件的目录路径")
    args = parser.parse_args()
    
    term_xlsx_dir_path = args.term
    loop_xlsx_dir_path = args.loop
    
    terminal_blocks = []
    xlsx_path = Path(term_xlsx_dir_path)

    reader = TerminalBlockReader()
    # 遍历文件夹及子文件夹中的所有 .xlsx 文件（排除临时文件 ~$ 开头）
    for file_path in sorted(xlsx_path.rglob("*.xlsx")):
        if file_path.name.startswith("~$"):
            continue
        print(f"正在处理文件: {file_path}")
        try:
            rows = reader.read_from_excel(str(file_path))
            terminal_blocks.extend(rows)
            print(f"已处理 {len(rows)} 条记录")
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")

    export_to_excel(terminal_blocks, "test.xlsx")

    # 打印结果
    print("端子排信息读取结果:")
    print("=" * 50)

    for terminal in terminal_blocks[:5]:  # 仅打印前5条作为示例
        print_terminal_info(terminal)
    print(f"... 共读取 {len(terminal_blocks)} 条记录 ...")

    # 假设 reader 已读取完所有 terminal_blocks（TerminalInfo 列表）
    graph = ConnectionGraph()
    graph.build_from_terminals(terminal_blocks)
    graph.load_connection_sheets(loop_xlsx_dir_path)

    # 根据回路查询组件
    export_circuit = "N"
    comp = graph.get_component_by_circuit(export_circuit)
    import pprint
    pprint.pprint(graph.summarize_component(comp))
    graph.export_drawio_xml(comp, Path(f"circuit_{export_circuit}.drawio"), title=f"Circuit {export_circuit}")
    
    # 导出所有回路组件的 drawio 文件, 没有回路号的不要导出, 端子少于2个的也不要导出
    all_comps = graph.get_all_components()
    for rep, comp in all_comps.items():
        # 检查组件中是否有回路节点
        has_circuit = any(isinstance(n, str) and n.startswith(ConnectionGraph.CIRCUIT_PREFIX) for n in comp)
        if not has_circuit:
            continue
        # 检查端子数量
        terminal_count = sum(1 for n in comp if isinstance(n, tuple))
        # if terminal_count < 2:
        #     continue

        output_file = Path(args.output_dir_path) / make_filename_for_component(comp, graph)
        # if args.format == "drawio":
        #     output_file = Path(args.output_dir_path) / f"component_{safe_rep}.drawio"
        # else:
            # output_file = Path(args.output_dir_path) / f"component_{safe_rep}.drawio.svg"
        graph.export_drawio_xml(comp, output_file, title=f"Component {rep}")

def test_single_circuit_filename_and_summary(tmp_path):
    # two terminals in same circuit C1
    t1 = TerminalInfo(
        cabinet_name="Cab1", circuit_number="C1", terminal_block_desc="", terminal_block="B1",
        terminal_number="1", side="L", internal_wiring=[], interconnect_terminal=[],
        function_desc="", external_wiring="", cable_core_number="", cable_number="",
        core_number="", cable_model="", opposite_device_number="", opposite_device_name="",
        remarks="", col_wire_text="", cable_type=""
    )
    t2 = TerminalInfo(
        cabinet_name="Cab1", circuit_number="C1", terminal_block_desc="", terminal_block="B1",
        terminal_number="2", side="L", internal_wiring=[], interconnect_terminal=[],
        function_desc="", external_wiring="", cable_core_number="", cable_number="",
        core_number="", cable_model="", opposite_device_number="", opposite_device_name="",
        remarks="", col_wire_text="", cable_type=""
    )

    g = ConnectionGraph()
    g.build_from_terminals([t1, t2])

    comps = g.get_all_components()
    # find component that contains our terminals
    found = False
    for rep, comp in comps.items():
        # summary should include circuit C1
        summary = g.summarize_component(comp)
        if "C1" in summary.get("circuits", []):
            found = True
            fname = make_filename_for_component(comp, g, prefix="component_test")
            assert "C1" in fname
            break
    assert found, "Expected component with circuit C1 not found"

def test_export_drawio_writes_file(tmp_path):
    # create two connected terminals (same circuit) and export
    t1 = TerminalInfo(
        cabinet_name="CabX", circuit_number="X1", terminal_block_desc="", terminal_block="Blk",
        terminal_number="10", side="R", internal_wiring=[], interconnect_terminal=[],
        function_desc="", external_wiring="", cable_core_number="", cable_number="",
        core_number="", cable_model="", opposite_device_number="", opposite_device_name="",
        remarks="", col_wire_text="", cable_type=""
    )
    t2 = TerminalInfo(
        cabinet_name="CabX", circuit_number="X1", terminal_block_desc="", terminal_block="Blk",
        terminal_number="11", side="R", internal_wiring=[], interconnect_terminal=[],
        function_desc="", external_wiring="", cable_core_number="", cable_number="",
        core_number="", cable_model="", opposite_device_number="", opposite_device_name="",
        remarks="", col_wire_text="", cable_type=""
    )

    g = ConnectionGraph()
    g.build_from_terminals([t1, t2])

    # pick a component that includes these terminals
    comps = g.get_all_components()
    comp_to_export = None
    for rep, comp in comps.items():
        if any(isinstance(n, tuple) and n[2] in ("10", "11") for n in comp):
            comp_to_export = comp
            break

    assert comp_to_export is not None, "Component to export not found"

    out_file = tmp_path / "test_export.drawio"
    # ensure directory exists and export
    g.export_drawio_xml(comp_to_export, out_file, title="TestExport")
    assert out_file.exists(), "Exported drawio file not created"
    content = out_file.read_text(encoding="utf-8")
    assert content.strip().startswith("<?xml"), "Exported file does not appear to be XML"

def test_multiple_circuits_in_same_component_filename(tmp_path):
    # create terminals such that two different circuit numbers end up in same connected component
    # t1 in C1, terminal number "1"
    t1 = TerminalInfo(
        cabinet_name="C_AB", circuit_number="C1", terminal_block_desc="", terminal_block="BLK1",
        terminal_number="1", side="L", internal_wiring=[], interconnect_terminal=[],
        function_desc="", external_wiring="", cable_core_number="", cable_number="",
        core_number="", cable_model="", opposite_device_number="", opposite_device_name="",
        remarks="", col_wire_text="", cable_type=""
    )
    # t2 in C2, terminal number "2", interconnect to "1" (same block) so they join component
    t2 = TerminalInfo(
        cabinet_name="C_AB", circuit_number="C2", terminal_block_desc="", terminal_block="BLK1",
        terminal_number="2", side="L", internal_wiring=[], interconnect_terminal=["1"],
        function_desc="", external_wiring="", cable_core_number="", cable_number="",
        core_number="", cable_model="", opposite_device_number="", opposite_device_name="",
        remarks="", col_wire_text="", cable_type=""
    )
    # t3 another terminal physically separate but in same circuit C1 to strengthen connection
    t3 = TerminalInfo(
        cabinet_name="C_AB", circuit_number="C1", terminal_block_desc="", terminal_block="BLK1",
        terminal_number="3", side="L", internal_wiring=[], interconnect_terminal=["2"],
        function_desc="", external_wiring="", cable_core_number="", cable_number="",
        core_number="", cable_model="", opposite_device_number="", opposite_device_name="",
        remarks="", col_wire_text="", cable_type=""
    )

    g = ConnectionGraph()
    g.build_from_terminals([t1, t2, t3])

    # find component that contains circuit numbers C1 and C2
    comps = g.get_all_components()
    matching = None
    for rep, comp in comps.items():
        summary = g.summarize_component(comp)
        circuits = set(summary.get("circuits", []))
        if {"C1", "C2"}.issubset(circuits):
            matching = comp
            break

    assert matching is not None, "Expected a component containing both C1 and C2"

    fname = make_filename_for_component(matching, g, prefix="multi_circuit")
    # filename should include both circuit codes
    assert "C1" in fname and "C2" in fname
    # also check that circuits order in filename is deterministic (sorted)
    circuits_in_fname = fname.split("_")[-1].split(".")[0]  # something like "C1_C2"
    assert "C1_C2" in circuits_in_fname or "C2_C1" in circuits_in_fname


# ============================================================================
# Utility Functions
# ============================================================================

def create_example_system() -> CabinetSystem:
    """
    创建一个示例机柜系统用于测试和演示
    
    Returns:
        CabinetSystem: 包含两个机柜的示例系统
    """
    system = CabinetSystem()
    
    # 机柜1：控制柜
    cabinet1 = Cabinet(number="CAB001", description="主控制柜")
    
    # 端子排1：电源端子排
    tb_power = TerminalBlock(name="TB_POWER", description="电源端子排")
    tb_power.add_terminal(Terminal(name="L1", circuit_number="PWR_L1", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="L2", circuit_number="PWR_L2", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="L3", circuit_number="PWR_L3", cable_number="CABLE_001"))
    tb_power.add_terminal(Terminal(name="N", circuit_number="PWR_N", cable_number="CABLE_001"))
    cabinet1.add_terminal_block(tb_power)
    
    # 装置1：PLC模块
    plc = Device(name="PLC_001", description="PLC模块")
    for i in range(8):
        plc.add_terminal(DeviceTerminal(name=f"DI{i+1}", row=i//4, col=i%4))
    cabinet1.add_device(plc)
    
    # 元件1：主电源开关
    main_switch = Component(
        name="QF1",
        component_type=ComponentType.SWITCH,
        description="主电源断路器"
    )
    main_switch.add_terminal(ComponentTerminal(name="1", position=0))
    main_switch.add_terminal(ComponentTerminal(name="2", position=1))
    main_switch.add_internal_connection("1", "2")
    cabinet1.add_component(main_switch)
    
    system.add_cabinet(cabinet1)
    
    # 机柜2：I/O扩展柜
    cabinet2 = Cabinet(number="CAB002", description="I/O扩展柜")
    
    # 端子排2：I/O端子排
    tb_io = TerminalBlock(name="TB_IO", description="I/O端子排")
    for i in range(1, 11):
        tb_io.add_terminal(Terminal(name=f"IO{i}"))
    cabinet2.add_terminal_block(tb_io)
    
    system.add_cabinet(cabinet2)
    
    # 添加连接
    connection1 = Connection(
        from_ref="CAB001/TB_POWER:L1",
        to_ref="CAB001/QF1:1",
        connection_type=ConnectionType.INTERNAL_WIRE,
        description="电源线"
    )
    system.add_connection(connection1)
    
    return system

