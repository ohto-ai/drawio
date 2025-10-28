from dataclasses import dataclass, field
from typing import List, Optional, Mapping, Union
from enum import Enum
import pandas as pd
import re

import logging
logger = logging.getLogger(__name__)

# 机柜信息
@dataclass
class Cabinet:
    id: str
    description: str = ""
    panel_terminal_blocks: List['TerminalBlock'] = field(default_factory=list)
    backend_connections: List['BackendConnection'] = field(default_factory=list)


class TerminalType(Enum):
    FRONT_PANEL = "front_panel"
    BACKEND_DEVICE = "backend_device"
    BACKEND_COMPONENT = "backend_component"

@dataclass
class TerminalRef:
    cabinet_id: str
    # 1. 前端面板是  terminal_block_id + terminal_name
    # 2. 后端装置是  device_group_id + terminal_name
    # 3. 后端元件是  component_id + terminal_name
    terminal_block_id: Optional[str] = None
    device_group_id: Optional[str] = None
    component_id: Optional[str] = None
    terminal_name: str = ""
    terminal_type: TerminalType = None

    def __str__(self):
        if self.terminal_type == TerminalType.FRONT_PANEL:
            return f"{self.cabinet_id}/@PANEL:{self.terminal_block_id}:{self.terminal_name}"
        elif self.terminal_type == TerminalType.BACKEND_DEVICE:
            return f"{self.cabinet_id}/@DEVICE_GROUP:{self.device_group_id}:{self.terminal_name}"
        elif self.terminal_type == TerminalType.BACKEND_COMPONENT:
            return f"{self.cabinet_id}/@COMPONENT:{self.component_id}:{self.terminal_name}"
        else:
            return f"{self.cabinet_id}/@UNKNOWN/{self.terminal_name}"

    def __hash__(self):
        return hash((self.cabinet_id, self.terminal_block_id, self.device_group_id, self.component_id, self.terminal_name, self.terminal_type))

@dataclass
class TerminalInfo:
    terminal_ref: TerminalRef
    description: str = ""
    direct_connect_terminal_refs: List[TerminalRef] = None                      # 直连端子名称，如: 1
    internal_connection_terminal_refs: List[TerminalRef] = field(default_factory=list)  # 机柜内连接端子名称，如: 4DK1:4 3D21
    external_connection_wire: Optional['GlobalWireRef'] = None       # <电缆编号>/<回路号>， 如: 1ABA01GG33122/A4431


@dataclass
class BackendConnection:
    """
    后端装置互联
    """
    from_terminal: TerminalRef
    to_terminal: TerminalRef


@dataclass
class GlobalWireRef:
    """
    全局线束引用
    """
    cable_id: Optional[str]
    loop_number: str    # 回路号


# 端子排
@dataclass
class TerminalBlock:
    id: str
    description: str = ""
    terminal_infos: Mapping[TerminalRef, TerminalInfo] = field(default_factory=dict)


# Data库
@dataclass
class TerminalDataModel:
    cabinets: Mapping[str, Cabinet] = field(default_factory=list)

    def load_xlsxs(self, file_paths: List[str]):
        """
        从多个Excel文件加载数据
        """
        for file_path in file_paths:
            self._load_xlsx(file_path)

    def _load_xlsx(self, file_path: str):

        try:
            xls = pd.ExcelFile(file_path)
        except Exception as e:
            logger.error(f"无法打开Excel文件 {file_path}: {e}")
            return
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            if "回路号" in df.columns and "端子号" in df.columns:
                self._process_front_panel_dataframe(df, description=f"{file_path} - {sheet_name}")
            elif "互联起点" in df.columns and "互联终点" in df.columns:
                self._process_backend_connections_dataframe(df, description=f"{file_path} - {sheet_name}")

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

    def _process_front_panel_dataframe(self, df: pd.DataFrame, description: str = ""):
        """
        从单个Excel文件加载数据
        示例Excel内容格式:
        回路号	端子排说明	端子排	端子号	左侧/右侧	内部配线	互联端子号	功能说明	外部接线	电缆芯编号	电缆编号	芯号	电缆型号	对侧设备编号	对侧设备名称	备注	COLWIRETExT	线缆型号	本端设备	本端设备编号
        A4611	电流回路		1	右侧	61LHa					1ABA03GG33120				512断路器保护屏 				512断路器CT端子箱	1ABA03GG003
        """
        last_cabinet_id = None
        last_terminal_block_id = None
        for index, row in df.iterrows():
            cabinet_id = TerminalDataModel.safe_str(row.get("本端设备编号", ""))
            if not cabinet_id:
                # 使用上一个机柜ID
                if last_cabinet_id:
                    cabinet_id = last_cabinet_id
                else:
                    logger.warning(f"{description}:{index}: 警告: 未找到机柜ID，且无上一个机柜ID可用，跳过该行数据。")
                    continue
            last_cabinet_id = cabinet_id
            cabinet = next((c for c in self.cabinets if c.id == cabinet_id), None)
            if not cabinet:
                cabinet = Cabinet(id=cabinet_id, description=TerminalDataModel.safe_str(row.get("本端设备", "")))
                self.cabinets.append(cabinet)

            terminal_block_id = TerminalDataModel.safe_str(row.get("端子排", ""))
            terminal_name = TerminalDataModel.safe_str(row.get("端子号", ""))
            # 为空， 使用上一个端子排
            if not terminal_block_id:
                if last_terminal_block_id:
                    terminal_block_id = last_terminal_block_id
                else:
                    # 特殊处理，如果端子号为1，则创建一个新的默认端子排ID
                    if terminal_name == "1":
                        terminal_block_id = f"{cabinet_id}_BLOCK_{len(cabinet.panel_terminal_blocks) + 1}"
                        logger.info(f"{description}:{index}: 信息: 端子排ID为空，且端子号为1，自动创建端子排ID: {terminal_block_id}。")
                    else:
                        logger.warning(f"{description}:{index}: 警告: 未找到端子排ID，且当前机柜无已存在端子排，跳过该行数据。")
                        continue
            last_terminal_block_id = terminal_block_id

            terminal_block = next((tb for tb in cabinet.panel_terminal_blocks if tb.id == terminal_block_id), None)
            if not terminal_block:
                terminal_block = TerminalBlock(id=terminal_block_id, description=TerminalDataModel.safe_str(row.get("端子排说明", "")))
                cabinet.panel_terminal_blocks.append(terminal_block)

            terminal_ref = TerminalRef(
                cabinet_id=cabinet_id,
                terminal_block_id=terminal_block_id,
                terminal_name=terminal_name,
                terminal_type=TerminalType.FRONT_PANEL
            )
            if terminal_ref in terminal_block.terminal_infos:
                terminal_info = terminal_block.terminal_infos[terminal_ref]
                logger.warning(f"{description}:{index}: 警告: 端子引用重复: {terminal_ref}, 已存在的端子信息将被更新。")
            else:
                terminal_info = TerminalInfo(terminal_ref=terminal_ref)
                terminal_block.terminal_infos[terminal_ref] = terminal_info

            terminal_info.description = TerminalDataModel.safe_str(row.get("功能说明", ""))
            direct_connects = TerminalDataModel.split_to_list(TerminalDataModel.safe_str(row.get("互联端子号", "")))
            if len(direct_connects) > 2:
                logger.warning(f"{description}:{index}: 警告: 端子 {terminal_ref} 的直连端子号超过2个: {direct_connects}。")
            direct_connects_refs = [
                TerminalRef(
                    cabinet_id=cabinet_id,
                    terminal_block_id=terminal_block_id,
                    terminal_name=dc,
                    terminal_type=TerminalType.FRONT_PANEL
                ) for dc in direct_connects
            ]
            terminal_info.direct_connect_terminal_refs = direct_connects_refs
            
            internal_connection = TerminalDataModel.split_to_list(TerminalDataModel.safe_str(row.get("内部配线", "")))
            internal_connection_terminal_refs = []
            for ic in internal_connection:
                match = re.match(r"([^:]+):(.+)", ic)
                if match:
                    ic_component_id = match.group(1).strip()
                    ic_terminal_name = match.group(2).strip()
                    ic_terminal_ref = TerminalRef(
                        cabinet_id=cabinet_id,
                        component_id=ic_component_id,
                        terminal_name=ic_terminal_name,
                        terminal_type=TerminalType.BACKEND_COMPONENT
                    )
                    internal_connection_terminal_refs.append(ic_terminal_ref)
                else:
                    # 自己单独一组
                    ic_terminal_ref = TerminalRef(
                        cabinet_id=cabinet_id,
                        device_group_id=ic,
                        terminal_name=ic,
                        terminal_type=TerminalType.BACKEND_DEVICE
                    )
                    internal_connection_terminal_refs.append(ic_terminal_ref)

            terminal_info.internal_connection_terminal_refs = internal_connection_terminal_refs

            cable_id = TerminalDataModel.safe_str(row.get("电缆编号", ""))
            loop_number = TerminalDataModel.safe_str(row.get("回路号", ""))
            terminal_info.external_connection_wire = GlobalWireRef(
                cable_id=cable_id if cable_id else None,
                loop_number=loop_number
            )


    def _process_backend_connections_dataframe(self, df: pd.DataFrame, description: str = ""):
        """
        处理后端装置互联数据
        示例Excel内容格式:
            设备编号	互联起点	互联终点
            1ABA03GG003	61LHn	1DK:1
            1ABA03GG003	1DK:1	61LHNa
        """
        for index, row in df.iterrows():
            cabinet_id = TerminalDataModel.safe_str(row.get("设备编号", ""))
            if not cabinet_id:
                logger.warning(f"{description}:{index}: 警告: 未找到机柜ID，跳过该行数据。")
                continue
            cabinet = next((c for c in self.cabinets if c.id == cabinet_id), None)
            if not cabinet:
                cabinet = Cabinet(id=cabinet_id)
                self.cabinets.append(cabinet)

            from_terminal_str = TerminalDataModel.safe_str(row.get("互联起点", ""))
            to_terminal_str = TerminalDataModel.safe_str(row.get("互联终点", ""))
            if not from_terminal_str or not to_terminal_str:
                logger.warning(f"{description}:{index}: 警告: 互联起点或终点为空，跳过该行数据。")
                continue

            def parse_terminal_ref(terminal_str: str) -> TerminalRef:
                if ':' in terminal_str:
                    parts = terminal_str.split(':', 1)
                    id_part = parts[0].strip()
                    name_part = parts[1].strip()
                    if re.match(r'^\d', id_part):
                        return TerminalRef(
                            cabinet_id=cabinet_id,
                            component_id=id_part,
                            terminal_name=name_part,
                            terminal_type=TerminalType.BACKEND_COMPONENT
                        )
                    else:
                        return TerminalRef(
                            cabinet_id=cabinet_id,
                            device_group_id=id_part,
                            terminal_name=name_part,
                            terminal_type=TerminalType.BACKEND_DEVICE
                        )
                else:
                    return TerminalRef(
                        cabinet_id=cabinet_id,
                        device_group_id=terminal_str,
                        terminal_name=terminal_str,
                        terminal_type=TerminalType.BACKEND_DEVICE
                    )

            from_terminal_ref = parse_terminal_ref(from_terminal_str)
            to_terminal_ref = parse_terminal_ref(to_terminal_str)

            backend_connection = BackendConnection(
                from_terminal=from_terminal_ref,
                to_terminal=to_terminal_ref
            )
            cabinet.backend_connections.append(backend_connection)

    def debug_print(self):
        for cabinet in self.cabinets:
            print(f"Cabinet ID: {cabinet.id}, Description: {cabinet.description}")
            for terminal_block in cabinet.panel_terminal_blocks:
                print(f"  Terminal Block ID: {terminal_block.id}, Description: {terminal_block.description}")
                for terminal_ref, terminal_info in terminal_block.terminal_infos.items():
                    print(f"    Terminal Ref: {terminal_ref}")
                    print(f"      Description: {terminal_info.description}")
                    print(f"      Direct Connects: {[str(dc) for dc in terminal_info.direct_connect_terminal_refs]}")
                    print(f"      Internal Connections: {[str(ic) for ic in terminal_info.internal_connection_terminal_refs]}")
                    if terminal_info.external_connection_wire:
                        print(f"      External Connection Wire: Cable ID: {terminal_info.external_connection_wire.cable_id}, Loop Number: {terminal_info.external_connection_wire.loop_number}")
                    else:
                        print(f"      External Connection Wire: None")
            for backend_connection in cabinet.backend_connections:
                print(f"  Backend Connection: From {backend_connection.from_terminal} To {backend_connection.to_terminal}")

if __name__ == "__main__":
    # 示例用法
    # excel_fold_path = r"C:\Users\OhtoAi\Downloads\继电保护室保护图纸 解析成果"
    excel_fold_path = r"C:\Users\OhtoAi\Downloads\小测试"
    # get all xlsx files in the folder, include subfolders
    import os
    excel_files = []
    for root, dirs, files in os.walk(excel_fold_path):
        for file in files:
            if file.startswith("~$"):
                continue
            if file.endswith(".xlsx"):
                excel_files.append(os.path.join(root, file))

    model = TerminalDataModel()
    model.load_xlsxs(excel_files)
    model.debug_print()
