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
    # device group 布局： device_group_id -> List[List[terminal_name]]（按行的二维列表）
    device_groups_layout: Dict[str, List[List[str]]] = field(default_factory=dict)


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
    order_in_terminal_block: int = None
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
    def __str__(self):
        # 使用可识别的前缀以便在 to_drawio_xml 中特殊处理
        # 格式: GLOBAL_WIRE:<cable_id or "">:<loop_number>
        return f"GLOBAL_WIRE:{self.cable_id or ''}:{self.loop_number}"
    def __repr__(self):
        return self.__str__()

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
    # virtual groups: 每项为一组逻辑上视为连通但不绘制具体边的节点集合（用于连通性计算）
    virtual_groups: List[Set[str]] = field(default_factory=list)
    # node_order: 保留每个端子的 order_in_terminal_block 值（用于按原顺序绘制）
    node_order: Dict[str, int] = field(default_factory=dict)

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
    def set_node_order(self, node_str: str, order: Optional[int]):
        if order is None:
            return
        self.node_order[node_str] = int(order)

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
        # 把 virtual_groups 中的节点视作连通（用于查询/拆分），但不在 edges 中绘制具体边
        for group in self.virtual_groups:
            members = list(group)
            if not members:
                continue
            first = members[0]
            for other in members[1:]:
                union(first, other)
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
            # 特殊处理全局线束，不放入任何组内
            if node_str.startswith("GLOBAL_WIRE:"):
                m = re.match(r"GLOBAL_WIRE:([^:]*):(.*)", node_str)
                if m:
                    return ("GLOBAL_WIRE", m.group(1), m.group(2))
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
        wire_nodes: List[str] = []
        for node in self.nodes:
            if node.startswith("GLOBAL_WIRE:"):
                # 收集全局线，不放入 groups 中
                wire_nodes.append(node)
                continue
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
            # group cell （不直接在这里放文本，文本作为单独子 cell 放在容器顶部）
            group_style = "rounded=1;strokeColor=#444444;fillColor=#f5f5f5;"
            group_cell = ET.SubElement(root, "mxCell", id=gid, value="", style=group_style, vertex="1", parent="1")

            # layout: 为标签和节点留出空间
            top_padding = 8
            label_height = 18
            between_label_and_nodes = 6
            bottom_padding = 8
            col_node_count = len(nodes)
            inner_nodes_height = max(node_height, col_node_count * (node_height + node_gap) - node_gap)
            group_height = top_padding + label_height + between_label_and_nodes + inner_nodes_height + bottom_padding
            ET.SubElement(group_cell, "mxGeometry", attrib={"x": str(x_col), "y": str(group_y_top), "width": str(group_width), "height": str(group_height), "as": "geometry"})

            # label cell：放在容器内顶部，明显可见，不会被节点遮挡
            label_id = gen_id()
            label_style = "text;html=1;align=left;verticalAlign=top;strokeColor=none;fillColor=none;fontStyle=1"
            label_cell = ET.SubElement(root, "mxCell", id=label_id, value=escape(g_label), style=label_style, vertex="1", parent=gid)
            ET.SubElement(label_cell, "mxGeometry", attrib={
                "x": str(12),
                "y": str(top_padding),
                "width": str(group_width - 24),
                "height": str(label_height),
                "as": "geometry"
            })

            # place nodes inside group（从标签下方开始）
            # 按 node_order 优先排序；若不存在 order，则尝试把标签解析为整数做数值排序，最后按字符串排序
            def sort_key(nstr):
                # 优先使用显式记录的 order_in_terminal_block
                if nstr in self.node_order:
                    return (0, self.node_order[nstr], 0, "")
                label = nstr.split(":")[-1]
                try:
                    num = int(label)
                    return (1, num, 0, "")
                except Exception:
                    return (2, 0, 0, label)

            ordered_nodes = sorted(nodes, key=sort_key)
            for ni, nstr in enumerate(ordered_nodes):
                nx = x_col + 12
                ny = group_y_top + top_padding + label_height + between_label_and_nodes + ni * (node_height + node_gap)
                # 使用圆形节点 + 旁边的文本标签
                label = nstr.split(":")[-1]
                circle_id = gen_id()
                node_cell_ids[nstr] = circle_id  # 边连接指向圆形节点 id
                circle_style = "shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000"
                circle_cell = ET.SubElement(root, "mxCell", id=circle_id, value="", style=circle_style, vertex="1", parent=gid)
                # 圆的大小使用 node_height（保证为正方形以形成圆）
                ET.SubElement(circle_cell, "mxGeometry", attrib={
                    "x": str(nx - x_col),
                    "y": str(ny - group_y_top),
                    "width": str(node_height),
                    "height": str(node_height),
                    "as": "geometry"
                })
                # 文本标签放在圆的右侧
                text_id = gen_id()
                text_style = "text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none"
                text_cell = ET.SubElement(root, "mxCell", id=text_id, value=escape(label), style=text_style, vertex="1", parent=gid)
                ET.SubElement(text_cell, "mxGeometry", attrib={
                    "x": str((nx - x_col) + node_height + 6),
                    "y": str(ny - group_y_top),
                    "width": str(max(10, node_width - node_height - 12)),
                    "height": str(node_height),
                    "as": "geometry"
                })

        # 为每个 GLOBAL_WIRE 创建一个单独的中转节点（不放入任何容器）
        wire_base_x = group_x + max(1, len(sorted_groups)) * (group_width + group_gap) + 40
        wire_index = 0
        for w in sorted(wire_nodes):
            # 解析显示标签
            m = re.match(r"GLOBAL_WIRE:([^:]*):(.*)", w)
            if m:
                cable = m.group(1) or ""
                loop = m.group(2) or ""
                label = f"{cable}/{loop}" if cable else loop
            else:
                label = w
            nid = gen_id()
            node_cell_ids[w] = nid
            wire_index += 1
            v = ET.SubElement(root, "mxCell", id=nid, value=escape(label),
                              style="shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#A67C00",
                              parent="1", vertex="1")
            ET.SubElement(v, "mxGeometry", attrib={"x": str(wire_base_x), "y": str(group_y_top + (wire_index - 1) * (node_height + node_gap)), "width": str(node_width // 2), "height": str(node_height), "as": "geometry"})

        # create standalone nodes for any endpoints missing from node_cell_ids (e.g. wires)
        # and create edge cells
        edge_style = "edgeStyle=elbowEdgeStyle;edgeRadius=0;rounded=0;html=1;strokeColor=#000000;startArrow=none;endArrow=none"
        # keep track of a simple free placement index for standalones
        standalone_index = 0
        for key, reasons in self.edges.items():
            a_str, b_str = self.repr_map[key]
            if a_str not in node_cell_ids:
                # 使用圆形表示端子，文本放在右侧
                circle_id = gen_id()
                node_cell_ids[a_str] = circle_id
                standalone_index += 1
                cx = 40
                cy = 40 + standalone_index * (node_height + node_gap)
                circle_cell = ET.SubElement(root, "mxCell", id=circle_id, value="",
                                            style="shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000",
                                            parent="1", vertex="1")
                ET.SubElement(circle_cell, "mxGeometry", attrib={"x": str(cx), "y": str(cy), "width": str(node_height), "height": str(node_height), "as": "geometry"})
                text_id = gen_id()
                text_cell = ET.SubElement(root, "mxCell", id=text_id, value=escape(a_str),
                                          style="text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none",
                                          parent="1", vertex="1")
                ET.SubElement(text_cell, "mxGeometry", attrib={"x": str(cx + node_height + 6), "y": str(cy), "width": str(max(10, node_width - node_height - 12)), "height": str(node_height), "as": "geometry"})

            if b_str not in node_cell_ids:
                circle_id = gen_id()
                node_cell_ids[b_str] = circle_id
                standalone_index += 1
                cx = 160
                cy = 40 + standalone_index * (node_height + node_gap)
                circle_cell = ET.SubElement(root, "mxCell", id=circle_id, value="",
                                            style="shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000",
                                            parent="1", vertex="1")
                ET.SubElement(circle_cell, "mxGeometry", attrib={"x": str(cx), "y": str(cy), "width": str(node_height), "height": str(node_height), "as": "geometry"})
                text_id = gen_id()
                text_cell = ET.SubElement(root, "mxCell", id=text_id, value=escape(b_str),
                                          style="text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none",
                                          parent="1", vertex="1")
                ET.SubElement(text_cell, "mxGeometry", attrib={"x": str(cx + node_height + 6), "y": str(cy), "width": str(max(10, node_width - node_height - 12)), "height": str(node_height), "as": "geometry"})

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
            elif "布局端子" in df.columns and "装置组编号" in df.columns:
                self._process_backend_devices_layout_dataframe(df, description=f"{file_path} - {sheet_name}")

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
                # update order
                terminal_info.order_in_terminal_block = len(terminal_block.terminal_infos)
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
                    # 自己单独一组
                    # 如果小写abcn结尾
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


    def _process_backend_devices_layout_dataframe(self, df: pd.DataFrame, description: str =""):
        """
        处理柜内装置布局图, 描述柜内端子所在的组以及每组内的行/列布局。
        表格列：设备编号  装置编号  装置组编号  布局端子
        每行代表该装置组的一行布局，布局端子内以 ';' 或 ',' 等分隔同一行内的端子。
        例如两行:
          61LH   61LH   61LHa;61LHb
          61LH   61LH   61LHc;61LHn
            设备编号	装置编号	装置组编号	布局端子
            1ABA03GG003	61LH	61LH	61LHa;61LHb
            1ABA03GG003	61LH	61LH	61LHc;61LHn
            1ABA01GG003	42LH	42LH1	42LHa
            1ABA01GG003	42LH	42LH1	42LHb
            1ABA01GG003	42LH	42LH2	42LHc
            1ABA01GG003	42LH	42LH2	42LHn
        表示 device_group_id=61LH 的一组包含 4 个端子，排布为 2 列、2 行（按读到的行顺序）。
        本函数会：
         - 把每个 cabinet 的 device_groups_layout 填充为二维行列表
         - 尝试在当前 cabinet 中查找与每个端子名匹配的 TerminalRef 实例，设置其 device_group_id
        """
        for index, row in df.iterrows():
            cabinet_id = TerminalDataModel.safe_str(row.get("设备编号", ""))
            if not cabinet_id:
                logger.warning(f"{description}:{index}: 未找到设备编号，跳过。")
                continue
            cabinet = next((c for c in self.cabinets if c.id == cabinet_id), None)
            if not cabinet:
                # 如果尚未创建 cabinet，则创建以便保存布局信息
                cabinet = Cabinet(id=cabinet_id)
                self.cabinets.append(cabinet)

            device_id = TerminalDataModel.safe_str(row.get("装置编号", ""))
            device_group_id = TerminalDataModel.safe_str(row.get("装置组编号", "")) or device_id
            layout_terminals_raw = TerminalDataModel.safe_str(row.get("布局端子", ""))
                

    def debug_print(self):
        for cabinet in self.cabinets:
            print(f"Cabinet ID: {cabinet.id}, Description: {cabinet.description}")
            for terminal_block in cabinet.panel_terminal_blocks:
                print(f"  Terminal Block ID: {terminal_block.id}, Description: {terminal_block.description}")
                for terminal_ref, terminal_info in terminal_block.terminal_infos.items():
                    print(f"    Terminal Ref: {terminal_ref}")
                    print(f"      Order: {terminal_info.order_in_terminal_block}")
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
                    # 保留端子原始顺序信息，供绘图时使用
                    graph.nodes.add(str(terminal_ref))
                    graph.set_node_order(str(terminal_ref), terminal_info.order_in_terminal_block)
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
            # 不自动绘制组内连线；记录 virtual group 用于连通性判断（查询时 a 可到达组内其他节点）
            if not items:
                continue
            members = {str(t) for t in items}
            # 保证组内节点至少存在于 graph.nodes 中（即使没有实际边，也能被拆分到同一个子图）
            for m in members:
                graph.nodes.add(m)
            graph.virtual_groups.append(members)

        for group_key, items in terminals_by_device_group.items():
            # device_group 同样不自动绘制组内连线，只记录为 virtual group 以保证连通性查询
            if not items:
                continue
            members = {str(t) for t in items}
            for m in members:
                graph.nodes.add(m)
            graph.virtual_groups.append(members)


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
            # 避免名称过长
            if len(fname_base) > 100:
                fname_base = fname_base[:100]
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

    model.export_drawio_groups(r"output_graphs")
