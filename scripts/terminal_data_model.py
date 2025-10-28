from dataclasses import dataclass, field
from typing import List, Optional, Mapping, Union, Set, Dict, Tuple
from enum import Enum
import pandas as pd
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import os

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

@dataclass
class ConnectionGraph:
    """
    存储无向连接边集合。边以字符串形式唯一化（使用端子或线缆的 __str__）。
    edges: Dict[frozenset({a_str,b_str})] -> set(reasons)
    repr_map: Dict[frozenset] -> (a_str, b_str) 保留一个有序表示用于输出
    """
    edges: Dict[frozenset, Set[str]] = field(default_factory=dict)
    repr_map: Dict[frozenset, Tuple[str, str]] = field(default_factory=dict)
    nodes: Set[str] = field(default_factory=set)

    def add_edge(self, a, b, reason: str):
        a_str = str(a)
        b_str = str(b)
        if a_str == b_str:
            return
        key = frozenset({a_str, b_str})
        if key not in self.edges:
            self.edges[key] = set()
            # choose a stable ordering for repr_map
            self.repr_map[key] = (a_str, b_str) if a_str <= b_str else (b_str, a_str)
        self.edges[key].add(reason)
        self.nodes.add(a_str)
        self.nodes.add(b_str)

    def get_edges(self):
        """返回边列表：每条边为 dict{a, b, reasons}"""
        out = []
        for key, reasons in self.edges.items():
            a_str, b_str = self.repr_map[key]
            out.append({"a": a_str, "b": b_str, "reasons": sorted(reasons)})
        return out

    def connected_components(self):
        """返回连通分量列表，每一项为端点字符串列表"""
        parent = {}
        def find(x):
            parent.setdefault(x, x)
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        def union(x,y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

        for key in self.edges.keys():
            a, b = self.repr_map[key]
            union(a, b)
        groups: Dict[str, List[str]] = {}
        for node in self.nodes:
            r = find(node)
            groups.setdefault(r, []).append(node)
        return list(groups.values())

    def split_into_subgraphs(self) -> List["ConnectionGraph"]:
        """
        根据连通分量拆分为若干子 ConnectionGraph，返回子图列表。
        每个子图只包含属于该连通分量的边与节点。
        """
        subgraphs: List[ConnectionGraph] = []
        comps = self.connected_components()
        for comp in comps:
            comp_set = set(comp)
            g = ConnectionGraph()
            for key, reasons in self.edges.items():
                a_str, b_str = self.repr_map[key]
                if a_str in comp_set and b_str in comp_set:
                    for reason in reasons:
                        g.add_edge(a_str, b_str, reason)
            subgraphs.append(g)
        return subgraphs

    def groups_edge_lists(self) -> List[List[Dict[str, object]]]:
        """
        返回每个子图对应的边列表（便于导出）。每项格式与 get_edges() 相同。
        """
        return [g.get_edges() for g in self.split_into_subgraphs()]

    def to_drawio_xml(self, file_path: str, title: Optional[str] = None,
                      group_gap: int = 80, group_width: int = 240,
                      node_width: int = 180, node_height: int = 36, node_gap: int = 8):
        """
        将当前 ConnectionGraph 导出为 draw.io (.drawio 即 xml) 文件。
        输出结构与示例保持一致：<mxfile><diagram><mxGraphModel>...</mxGraphModel></diagram></mxfile>
        布局规则同前：按 PANEL/DEVICE_GROUP/COMPONENT 分组；组内按行排列；组之间按列排列。
        """
        def node_group_key(node_str: str):
            if "/@PANEL:" in node_str:
                m = re.match(r"([^/]+)/@PANEL:([^:]+):(.+)", node_str)
                if m:
                    return ("PANEL", m.group(1), m.group(2))
            if "/@DEVICE_GROUP:" in node_str:
                m = re.match(r"([^/]+)/@DEVICE_GROUP:([^:]+):(.+)", node_str)
                if m:
                    return ("DEVICE_GROUP", m.group(1), m.group(2))
            if "/@COMPONENT:" in node_str:
                m = re.match(r"([^/]+)/@COMPONENT:([^:]+):(.+)", node_str)
                if m:
                    return ("COMPONENT", m.group(1), m.group(2))
            m = re.match(r"([^/]+)/", node_str)
            if m:
                return ("CABINET", m.group(1), "")
            return ("UNGROUPED", "", "")

        groups: Dict[Tuple[str,str,str], List[str]] = {}
        for node in self.nodes:
            key = node_group_key(node)
            groups.setdefault(key, []).append(node)

        sorted_groups = sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2]))

        # id generator
        next_id = 2
        def gen_id():
            nonlocal next_id
            next_id += 1
            return str(next_id)

        node_cell_ids: Dict[str, str] = {}
        group_cell_ids: Dict[Tuple[str,str,str], str] = {}

        # build mxfile -> diagram -> mxGraphModel (match example)
        mxfile = ET.Element("mxfile", attrib={"host":"127.0.0.1"})
        diagram = ET.SubElement(mxfile, "diagram", name=title or "Graph", id="diagram1")
        mxgraph = ET.SubElement(diagram, "mxGraphModel", attrib={
            "dx":"0","dy":"0","grid":"1","gridSize":"10","guides":"1","tooltips":"1",
            "connect":"1","arrows":"1","fold":"1","page":"1","pageScale":"1","pageWidth":"827","pageHeight":"1169"
        })
        root = ET.SubElement(mxgraph, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")

        # layout placement params
        group_x = 40
        group_y_top = 40

        for gi, (gkey, nodes) in enumerate(sorted_groups):
            x_col = group_x + gi * (group_width + group_gap)
            gid = gen_id()
            group_cell_ids[gkey] = gid
            g_label = f"{gkey[0]}:{gkey[2] or gkey[1]}"
            # group cell
            group_cell = ET.SubElement(root, "mxCell", id=gid, value=escape(g_label),
                                       style="rounded=1;strokeColor=#444444;fillColor=#f5f5f5;", vertex="1", parent="1")
            group_padding = 12
            col_node_count = len(nodes)
            group_height = max(node_height, col_node_count * (node_height + node_gap) - node_gap) + group_padding*2
            ET.SubElement(group_cell, "mxGeometry", attrib={"x": str(x_col), "y": str(group_y_top), "width": str(group_width), "height": str(group_height), "as": "geometry"})

            # place nodes inside group
            for ni, nstr in enumerate(sorted(nodes)):
                nx = x_col + group_padding
                ny = group_y_top + group_padding + ni * (node_height + node_gap)
                nid = gen_id()
                node_cell_ids[nstr] = nid
                label = nstr.split(":")[-1]
                node_style = "shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000"
                node_cell = ET.SubElement(root, "mxCell", id=nid, value=escape(label), style=node_style, vertex="1", parent=gid)
                ET.SubElement(node_cell, "mxGeometry", attrib={"x": str(nx - x_col), "y": str(ny - group_y_top), "width": str(node_width), "height": str(node_height), "as": "geometry"})

        # create standalone nodes for any endpoints missing from node_cell_ids (e.g. wires)
        # and create edge cells
        edge_style = "edgeStyle=elbowEdgeStyle;edgeRadius=0;rounded=0;html=1;strokeColor=#000000;startArrow=none;endArrow=none"
        # keep track of a simple free placement index for standalones
        standalone_index = 0
        for key, reasons in self.edges.items():
            a_str, b_str = self.repr_map[key]
            if a_str not in node_cell_ids:
                nid = gen_id()
                node_cell_ids[a_str] = nid
                standalone_index += 1
                v = ET.SubElement(root, "mxCell", id=nid, value=escape(a_str),
                                  style="shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000",
                                  parent="1", vertex="1")
                ET.SubElement(v, "mxGeometry", attrib={"x": str(40), "y": str(40 + standalone_index * (node_height + node_gap)), "width": str(node_width), "height": str(node_height), "as": "geometry"})
            if b_str not in node_cell_ids:
                nid = gen_id()
                node_cell_ids[b_str] = nid
                standalone_index += 1
                v = ET.SubElement(root, "mxCell", id=nid, value=escape(b_str),
                                  style="shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000",
                                  parent="1", vertex="1")
                ET.SubElement(v, "mxGeometry", attrib={"x": str(160), "y": str(40 + standalone_index * (node_height + node_gap)), "width": str(node_width), "height": str(node_height), "as": "geometry"})

            edge_id = gen_id()
            reason_label = ""  # 保持连线上不显示长文本，避免遮挡；如需显示可改为 ",".join(sorted(reasons))
            edge_attrib = {"id": edge_id, "edge":"1", "parent":"1", "source": node_cell_ids[a_str], "target": node_cell_ids[b_str], "value": escape(reason_label), "style": edge_style}
            edge_el = ET.SubElement(root, "mxCell", **edge_attrib)
            ET.SubElement(edge_el, "mxGeometry", attrib={"relative": "1", "as": "geometry"})

        # write file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        tree = ET.ElementTree(mxfile)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)

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
                    # 如果小写abcn结尾
                    if ic.endswith(('a', 'b', 'c', 'n')):
                        ic_device_group_id = ic[:-1]
                    else:
                        ic_device_group_id = ic
                    ic_terminal_ref = TerminalRef(
                        cabinet_id=cabinet_id,
                        device_group_id=ic_device_group_id,
                        terminal_name=ic,
                        terminal_type=TerminalType.BACKEND_DEVICE
                    )
                    internal_connection_terminal_refs.append(ic_terminal_ref)

            terminal_info.internal_connection_terminal_refs = internal_connection_terminal_refs

            cable_id = TerminalDataModel.safe_str(row.get("电缆编号", ""))
            loop_number = TerminalDataModel.safe_str(row.get("回路号", ""))
            if not cable_id:
                logger.warning(f"{description}:{index}: 警告: 端子 {terminal_ref} 的电缆编号为空，将仅使用回路号区分。")
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
                    if terminal_str.endswith(('a', 'b', 'c', 'n')):
                        ic_device_group_id = terminal_str[:-1]
                    else:
                        ic_device_group_id = terminal_str
                    return TerminalRef(
                        cabinet_id=cabinet_id,
                        device_group_id=ic_device_group_id,
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

    def build_connection_graph_groups(self) -> List[ConnectionGraph]:
        """
        构建完整连接图并按连通性拆分，返回子图列表（每个子图为一个 ConnectionGraph）。
        方便按组导出到 drawio/CSV/其他格式。
        """
        full_graph = self.build_connection_graph()
        return full_graph.split_into_subgraphs()
    # 新增：根据规则构建连接图
    def build_connection_graph(self) -> ConnectionGraph:
        """
        根据规则构建连接集合（无向图）。
        规则参考：
        1. TerminalInfo.direct_connect_terminal_refs
        2. TerminalInfo.internal_connection_terminal_refs
        3. TerminalInfo.external_connection_wire -> 与 GlobalWireRef 连线
        4. Cabinet.backend_connections
        5. 相同 component_id 的 BACKEND_COMPONENT 端子互联
        6. 相同 device_group_id 的 BACKEND_DEVICE 端子互联
        """
        graph = ConnectionGraph()

        for cabinet in self.cabinets:
            # 1-3: 遍历面板端子及其TerminalInfo
            for tb in cabinet.panel_terminal_blocks:
                for terminal_ref, terminal_info in tb.terminal_infos.items():
                    if terminal_info.direct_connect_terminal_refs:
                        for dc in terminal_info.direct_connect_terminal_refs:
                            graph.add_edge(terminal_ref, dc, "direct_connect")
                    for ic in terminal_info.internal_connection_terminal_refs:
                        graph.add_edge(terminal_ref, ic, "internal_connection")
                    if terminal_info.external_connection_wire:
                        graph.add_edge(terminal_ref, terminal_info.external_connection_wire, "external_wire")
            # 4: cabinet backend_connections
            for bc in cabinet.backend_connections:
                graph.add_edge(bc.from_terminal, bc.to_terminal, "backend_connection")

        # 5 & 6: group by component_id/device_group_id 并将组内所有端子两两连接（或连到组代表）
        terminals_by_component: Dict[Tuple[str, str], List[TerminalRef]] = {}
        terminals_by_device_group: Dict[Tuple[str, str], List[TerminalRef]] = {}

        def collect_terminal(t: TerminalRef):
            if t is None:
                return
            if t.component_id:
                terminals_by_component.setdefault((t.cabinet_id, t.component_id), []).append(t)
            if t.device_group_id:
                terminals_by_device_group.setdefault((t.cabinet_id, t.device_group_id), []).append(t)

        for cabinet in self.cabinets:
            for tb in cabinet.panel_terminal_blocks:
                for terminal_ref, terminal_info in tb.terminal_infos.items():
                    collect_terminal(terminal_ref)
                    if terminal_info.direct_connect_terminal_refs:
                        for dc in terminal_info.direct_connect_terminal_refs:
                            collect_terminal(dc)
                    for ic in terminal_info.internal_connection_terminal_refs:
                        collect_terminal(ic)
            for bc in cabinet.backend_connections:
                collect_terminal(bc.from_terminal)
                collect_terminal(bc.to_terminal)

        for group_key, items in terminals_by_component.items():
            if len(items) <= 1:
                continue
            rep = items[0]
            for other in items[1:]:
                graph.add_edge(rep, other, f"same_component:{group_key[1]}")

        for group_key, items in terminals_by_device_group.items():
            if len(items) <= 1:
                continue
            rep = items[0]
            for other in items[1:]:
                graph.add_edge(rep, other, f"same_device_group:{group_key[1]}")

        return graph

    def build_connection_graph_groups(self) -> List[ConnectionGraph]:
        """
        构建完整连接图并按连通性拆分，返回子图列表（每个子图为一个 ConnectionGraph）。
        方便按组导出到 drawio/CSV/其他格式。
        """
        full_graph = self.build_connection_graph()
        return full_graph.split_into_subgraphs()

    def export_drawio_groups(self, out_folder: str):
        """
        将按连通分量拆分后的每个子图导出为 drawio 文件（.drawio）。
        输出文件名与标题由该子图内所有端子的 terminal_block_id/device_group_id/component_id 去重后组合而成。
        """
        os.makedirs(out_folder, exist_ok=True)
        groups = self.build_connection_graph_groups()
        out_paths = []
        for i, g in enumerate(groups, start=1):
            tb_ids = set()
            dg_ids = set()
            comp_ids = set()
            for node in g.nodes:
                m = re.match(r"[^/]+/@PANEL:([^:]+):", node)
                if m:
                    tb_ids.add(m.group(1))
                    continue
                m = re.match(r"[^/]+/@DEVICE_GROUP:([^:]+):", node)
                if m:
                    dg_ids.add(m.group(1))
                    continue
                m = re.match(r"[^/]+/@COMPONENT:([^:]+):", node)
                if m:
                    comp_ids.add(m.group(1))
                    continue

            parts = []
            if tb_ids:
                parts.append("TB:" + ",".join(sorted(tb_ids)))
            if dg_ids:
                parts.append("DG:" + ",".join(sorted(dg_ids)))
            if comp_ids:
                parts.append("CMP:" + ",".join(sorted(comp_ids)))
            title = " | ".join(parts) if parts else f"Group {i}"

            # sanitize filename (移除/替换不安全字符)
            fname_base = re.sub(r'[\\/:*?"<>|\s]+', '_', title)
            if not fname_base:
                fname_base = f"group_{i}"
            fp = os.path.join(out_folder, f"{fname_base}.drawio")

            g.to_drawio_xml(fp, title=title)
            out_paths.append(fp)
        return out_paths

if __name__ == "__main__":
    # 示例用法
    # excel_fold_path = r"C:\Users\OhtoAi\Downloads\继电保护室保护图纸 解析成果"
    excel_fold_path = r"C:\Users\OhtoAi\Downloads\小测试"
    # get all xlsx files in the folder, include subfolders
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
    graph_groups = model.build_connection_graph_groups()
    for i, g in enumerate(graph_groups, 1):
        print(f"Group {i}:")
        for e in g.get_edges():
            print(e)

    model.export_drawio_groups(r"C:\Users\OhtoAi\Downloads\小测试\output_graphs")
