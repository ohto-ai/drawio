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

# 设置debug
logging.basicConfig(level=logging.DEBUG)

# 预定义的 component 图形映射：类型名 -> mxCell style + 默认宽高/值
# 只在能识别类型时使用，未识别则回退为文字标签
COMPONENT_GRAPHICS: Dict[str, Dict[str, object]] = {
    # 闭合开关（示例：开关闭合状态）
    "闭合开关": {
        "style": "html=1;shape=mxgraph.electrical.electro-mechanical.singleSwitch;aspect=fixed;elSwitchState=on;",
        "width": 75,
        "height": 20,
        "value": ""
    },
    # 刀开关（示例：开关断开状态）
    "刀开关": {
        "style": "html=1;shape=mxgraph.electrical.electro-mechanical.singleSwitch;aspect=fixed;elSwitchState=off;",
        "width": 75,
        "height": 20,
        "value": ""
    },
    "双刀开关": {
        "style": "html=1;verticalAlign=top;shape=mxgraph.electrical.electro-mechanical.dpst2;elSwitchState=off;",
        "width": 75,
        "height": 40,
    },
    "压板": {
        "style": "shape=image;verticalLabelPosition=bottom;labelBackgroundColor=default;verticalAlign=top;aspect=fixed;imageAspect=0;editableCssRules=.*;image=data:image/svg+xml,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiBzdHlsZT0iYmFja2dyb3VuZDogdHJhbnNwYXJlbnQ7IGJhY2tncm91bmQtY29sb3I6IHRyYW5zcGFyZW50OyBjb2xvci1zY2hlbWU6IGxpZ2h0IGRhcms7IiB2ZXJzaW9uPSIxLjEiIHdpZHRoPSI2MCIgaGVpZ2h0PSIyMCIgdmlld0JveD0iMSAwLjUgNjAgMjAiPiYjeGE7ICAgIDxkZWZzLz4mI3hhOyAgICA8Zz4mI3hhOyAgICAgICAgPGcgZGF0YS1jZWxsLWlkPSIwIj4mI3hhOyAgICAgICAgICAgIDxnIGRhdGEtY2VsbC1pZD0iMSI+JiN4YTsgICAgICAgICAgICAgICAgPGcgZGF0YS1jZWxsLWlkPSI5N21DNmdrUEpnZTR6V3JraEVCRy0xIj4mI3hhOyAgICAgICAgICAgICAgICAgICAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMC41LDAuNSkiPiYjeGE7ICAgICAgICAgICAgICAgICAgICAgICAgPGVsbGlwc2UgY3g9IjEwLjUiIGN5PSIxMCIgcng9IjEwIiByeT0iMTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzAwMDAwMCIgcG9pbnRlci1ldmVudHM9ImFsbCIgc3R5bGU9InN0cm9rZTogbGlnaHQtZGFyayhyZ2IoMCwgMCwgMCksIHJnYigyNTUsIDI1NSwgMjU1KSk7Ii8+JiN4YTsgICAgICAgICAgICAgICAgICAgIDwvZz4mI3hhOyAgICAgICAgICAgICAgICA8L2c+JiN4YTsgICAgICAgICAgICAgICAgPGcgZGF0YS1jZWxsLWlkPSI5N21DNmdrUEpnZTR6V3JraEVCRy0yIj4mI3hhOyAgICAgICAgICAgICAgICAgICAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMC41LDAuNSkiPiYjeGE7ICAgICAgICAgICAgICAgICAgICAgICAgPGVsbGlwc2UgY3g9IjUwLjUiIGN5PSIxMCIgcng9IjEwIiByeT0iMTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzAwMDAwMCIgcG9pbnRlci1ldmVudHM9ImFsbCIgc3R5bGU9InN0cm9rZTogbGlnaHQtZGFyayhyZ2IoMCwgMCwgMCksIHJnYigyNTUsIDI1NSwgMjU1KSk7Ii8+JiN4YTsgICAgICAgICAgICAgICAgICAgIDwvZz4mI3hhOyAgICAgICAgICAgICAgICA8L2c+JiN4YTsgICAgICAgICAgICAgICAgPGcgZGF0YS1jZWxsLWlkPSI5N21DNmdrUEpnZTR6V3JraEVCRy0zIj4mI3hhOyAgICAgICAgICAgICAgICAgICAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMC41LDAuNSkiPiYjeGE7ICAgICAgICAgICAgICAgICAgICAgICAgPHBhdGggZD0iTSAxMCAwLjA4IEwgNTAuNSAwIiBmaWxsPSJub25lIiBzdHJva2U9IiMwMDAwMDAiIHN0cm9rZS1taXRlcmxpbWl0PSIxMCIgcG9pbnRlci1ldmVudHM9InN0cm9rZSIgc3R5bGU9InN0cm9rZTogbGlnaHQtZGFyayhyZ2IoMCwgMCwgMCksIHJnYigyNTUsIDI1NSwgMjU1KSk7Ii8+JiN4YTsgICAgICAgICAgICAgICAgICAgIDwvZz4mI3hhOyAgICAgICAgICAgICAgICA8L2c+JiN4YTsgICAgICAgICAgICAgICAgPGcgZGF0YS1jZWxsLWlkPSI5N21DNmdrUEpnZTR6V3JraEVCRy00Ij4mI3hhOyAgICAgICAgICAgICAgICAgICAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMC41LDAuNSkiPiYjeGE7ICAgICAgICAgICAgICAgICAgICAgICAgPHBhdGggZD0iTSAxMC41IDIwIEwgNTAuNSAyMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMDAwMDAwIiBzdHJva2UtbWl0ZXJsaW1pdD0iMTAiIHBvaW50ZXItZXZlbnRzPSJzdHJva2UiIHN0eWxlPSJzdHJva2U6IGxpZ2h0LWRhcmsocmdiKDAsIDAsIDApLCByZ2IoMjU1LCAyNTUsIDI1NSkpOyIvPiYjeGE7ICAgICAgICAgICAgICAgICAgICA8L2c+JiN4YTsgICAgICAgICAgICAgICAgPC9nPiYjeGE7ICAgICAgICAgICAgPC9nPiYjeGE7ICAgICAgICA8L2c+JiN4YTsgICAgPC9nPiYjeGE7PC9zdmc+;",
        "width": 60,
        "height": 20,
        "value": ""
    },
    "LED": {
        "style": "html=1;verticalAlign=top;shape=mxgraph.electrical.miscellaneous.light_bulb;",
        "width": 40,
        "height": 40,
    },
    # 可按需添加更多映射，键可以是中文类型或从 Excel 中读取到的原始类型字符串
}

# 机柜信息
@dataclass
class Cabinet:
    id: str
    description: str = ""
    panel_terminal_blocks: List['TerminalBlock'] = field(default_factory=list)
    backend_connections: List['BackendConnection'] = field(default_factory=list)
    # device group 布局： device_group_id -> List[List[terminal_name]]（按行的二维列表）
    # device_groups_layout: Dict[str, List[List[str]]] = field(default_factory=dict)
    backend_components: Dict[str, 'BackendComponentInfo'] = field(default_factory=dict)
    backend_device_groups: Dict[str, 'BackendDeviceGroupInfo'] = field(default_factory=dict)
    


class TerminalType(Enum):
    FRONT_PANEL = "front_panel"
    BACKEND_DEVICE = "backend_device"
    BACKEND_COMPONENT = "backend_component"

class BackendComponentInfo:
    component_id: str
    component_type: str
    terminal_refs: List['TerminalRef']

class BackendDeviceGroupInfo:
    device_id: str
    device_group_id: str
    terminal_refs: List['TerminalRef']
    # 2D layout: List[List[Optional[TerminalRef]]]
    # Each inner list represents a row, None represents an empty cell
    terminal_layout: List[List[Optional['TerminalRef']]] = None

@dataclass
class TerminalRef:
    cabinet_id: str
    # 1. 前端面板是  terminal_block_id + terminal_name
    # 2. 后端装置是  device_group_id + terminal_name (device_group_id可选)
    # 3. 后端元件是  component_id + terminal_name
    terminal_block_id: Optional[str] = None
    component_id: Optional[str] = None
    device_group_id: Optional[str] = None
    terminal_name: str = ""
    terminal_type: TerminalType = None

    def __str__(self):
        if self.terminal_type == TerminalType.FRONT_PANEL:
            return f"{self.cabinet_id}/@PANEL:{self.terminal_block_id}:{self.terminal_name}"
        elif self.terminal_type == TerminalType.BACKEND_DEVICE:
            if self.device_group_id:
                return f"{self.cabinet_id}/@DEVICE:{self.device_group_id}:{self.terminal_name}"
            else:
                return f"{self.cabinet_id}/@DEVICE:{self.terminal_name}"
        elif self.terminal_type == TerminalType.BACKEND_COMPONENT:
            return f"{self.cabinet_id}/@COMPONENT:{self.component_id}:{self.terminal_name}"
        else:
            return f"{self.cabinet_id}/@UNKNOWN/{self.terminal_name}"

    def __hash__(self):
        return hash((self.cabinet_id, self.terminal_block_id, self.component_id, self.device_group_id, self.terminal_name, self.terminal_type))

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
        return f"@GLOBAL_WIRE:{self.cable_id or ''}:{self.loop_number}"
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
                      node_width: int = 180, node_height: int = 36, node_gap: int = 8,
                      component_types: Optional[Dict[Tuple[str, str], str]] = None,
                      device_group_layouts: Optional[Dict[Tuple[str, str], List[List[Optional[str]]]]] = None):
        """
        将当前 ConnectionGraph 导出为 draw.io (.drawio 即 xml) 文件。
        输出结构与示例保持一致：<mxfile><diagram><mxGraphModel>...</mxGraphModel></diagram></mxfile>
        布局规则同前：按 PANEL/DEVICE/COMPONENT 分组；组内按行排列；组之间按列排列。
        """
        def node_group_key(node_str: str):
            # 特殊处理全局线束，不放入任何组内
            if node_str.startswith("@GLOBAL_WIRE:"):
                m = re.match(r"GLOBAL_WIRE:([^:]*):(.*)", node_str)
                if m:
                    return ("@GLOBAL_WIRE", m.group(1), m.group(2))
            if "/@PANEL:" in node_str:
                m = re.match(r"([^/]+)/@PANEL:([^:]+):(.+)", node_str)
                if m:
                    return ("PANEL", m.group(1), m.group(2))
            if "/@DEVICE:" in node_str:
                # Try with device_group_id first (3 parts)
                m = re.match(r"([^/]+)/@DEVICE:([^:]+):(.+)", node_str)
                if m:
                    return ("DEVICE", m.group(1), m.group(2))
                # Fallback to no device_group_id (2 parts) - for backward compatibility
                m = re.match(r"([^/]+)/@DEVICE:(.+)", node_str)
                if m:
                    return ("DEVICE", m.group(1), "")
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
            if node.startswith("@GLOBAL_WIRE:"):
                # 收集全局线，不放入 groups 中
                wire_nodes.append(node)
                continue
            key = node_group_key(node)
            groups.setdefault(key, []).append(node)

        sorted_groups = sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2]))

        # 基本布局起点（提前定义，后续计算列/行位置时需要引用）
        group_x = 40
        group_y_top = 40

        from collections import deque

        # 布局策略：基于组间连通关系进行逻辑布局（距离层级 -> 列；列内堆叠）
        # 先计算每个组的高度（与原来一致），用于列内堆叠
        top_padding = 16
        label_height = 18
        between_label_and_nodes = 6
        bottom_padding = 20
        group_heights: Dict[Tuple[str,str,str], int] = {}
        for gkey, nodes in sorted_groups:
            col_node_count = len(nodes)
            # For COMPONENT groups, check if we have actual graphic dimensions
            if gkey[0] == "COMPONENT":
                comp_cabinet = gkey[1]
                comp_id = gkey[2] or ""
                comp_type_str = None
                if component_types:
                    comp_type_str = component_types.get((comp_cabinet, comp_id))
                comp_type_str = comp_type_str or comp_id or ""
                gfx = COMPONENT_GRAPHICS.get(comp_type_str)
                if gfx:
                    # Use actual graphic height from COMPONENT_GRAPHICS
                    g_h = int(gfx.get("height", node_height))
                    inner_nodes_height = g_h
                else:
                    # Fallback to default calculation for text-based components
                    inner_nodes_height = max(node_height, col_node_count * (node_height + node_gap) - node_gap)
            else:
                inner_nodes_height = max(node_height, col_node_count * (node_height + node_gap) - node_gap)
            group_heights[gkey] = top_padding + label_height + between_label_and_nodes + inner_nodes_height + bottom_padding

        # node -> gkey 映射（加速查找）
        node_to_group: Dict[str, Tuple[str,str,str]] = {}
        for gkey, nodes in sorted_groups:
            for n in nodes:
                node_to_group[n] = gkey

        # 根据 edges 构建组间邻接关系（若边跨组，则组相连）
        adj: Dict[Tuple[str,str,str], Set[Tuple[str,str,str]]] = {gkey:set() for gkey,_ in sorted_groups}
        for key in self.edges.keys():
            a_str, b_str = self.repr_map[key]
            g_a = node_to_group.get(a_str)
            g_b = node_to_group.get(b_str)
            if g_a and g_b and g_a != g_b:
                adj[g_a].add(g_b)
                adj[g_b].add(g_a)

        # BFS 分配列号（以距离为列），对每个连通子集分配起点为当前子集度数最大的组
        unvisited = set(adj.keys())
        group_column: Dict[Tuple[str,str,str], int] = {}
        while unvisited:
            start = max(unvisited, key=lambda k: len(adj[k]))
            dq = deque()
            dq.append((start, 0))
            group_column[start] = 0
            unvisited.remove(start)
            while dq:
                cur, dist = dq.popleft()
                for nb in sorted(adj[cur], key=lambda k: (len(adj[k]), k)):
                    if nb in group_column:
                        continue
                    group_column[nb] = dist + 1
                    if nb in unvisited:
                        unvisited.remove(nb)
                    dq.append((nb, dist+1))

        # 收集每列的组，并在列内按度数降序（稳定）排列
        columns: Dict[int, List[Tuple[str,str,str]]] = {}
        for gkey, _ in sorted_groups:
            col = group_column.get(gkey, 0)
            columns.setdefault(col, []).append(gkey)
        for col, items in columns.items():
            items.sort(key=lambda k: (-len(adj.get(k, [])), k))

        # 改进布局：
        # 1) 列顺序优化（局部相邻列交换，减少跨列交叉）
        # 2) 列内按重心（barycenter）排序，尽量把与同列外相连较近的组放在一起，减少交叉
        # 3) 处理柜体间重叠：若 cabinet 的外框在水平上与之前的 cabinet 重叠，则把后续列整体右移以避免重叠

        # 生成初始列顺序
        col_order = sorted(columns.keys())

        # 预计算列内每组的行索引（固定排序）
        col_row_index: Dict[int, Dict[Tuple[str,str,str], int]] = {}
        for c, items in columns.items():
            col_row_index[c] = {g: idx for idx, g in enumerate(items)}

        # 计算交叉代价函数（同之前实现的贪心相邻交换）
        def total_crossings_for_order(order: List[int]) -> int:
            pos_map = {col: i for i, col in enumerate(order)}
            edges_between: Dict[Tuple[int,int], List[Tuple[int,int]]] = {}
            for key in self.edges.keys():
                a_str, b_str = self.repr_map[key]
                g_a = node_to_group.get(a_str)
                g_b = node_to_group.get(b_str)
                if not g_a or not g_b or g_a == g_b:
                    continue
                # 找到两端所在列（原列编号）
                col_a = group_column.get(g_a)
                col_b = group_column.get(g_b)
                if col_a is None or col_b is None or col_a == col_b:
                    continue
                pos_a = pos_map.get(col_a)
                pos_b = pos_map.get(col_b)
                if pos_a is None or pos_b is None or pos_a == pos_b:
                    continue
                if pos_a < pos_b:
                    left_col, right_col = col_a, col_b
                    left_row = col_row_index[left_col].get(g_a, 0)
                    right_row = col_row_index[right_col].get(g_b, 0)
                else:
                    left_col, right_col = col_b, col_a
                    left_row = col_row_index[left_col].get(g_b, 0)
                    right_row = col_row_index[right_col].get(g_a, 0)
                edges_between.setdefault((pos_map[left_col], pos_map[right_col]), []).append((left_row, right_row))
            total = 0
            for lst in edges_between.values():
                lst.sort(key=lambda lr: lr[0])
                right_seq = [r for _, r in lst]
                inv = 0
                for i in range(len(right_seq)):
                    for j in range(i+1, len(right_seq)):
                        if right_seq[i] > right_seq[j]:
                            inv += 1
                total += inv
            return total

        # 局部相邻列交换优化（贪心）
        if len(col_order) > 1:
            improved = True
            max_iters = max(10, len(col_order) * 3)
            it = 0
            best_order = col_order[:]
            best_score = total_crossings_for_order(best_order)
            while improved and it < max_iters:
                improved = False
                it += 1
                for i in range(len(best_order) - 1):
                    cand = best_order[:]
                    cand[i], cand[i+1] = cand[i+1], cand[i]
                    score = total_crossings_for_order(cand)
                    if score < best_score:
                        best_score = score
                        best_order = cand
                        improved = True
                        break
            col_order = best_order

        # 列内按重心（barycenter）重新排序，降低列间交叉（不改变组内终端顺序）
        col_pos_map = {col: idx for idx, col in enumerate(col_order)}
        for col in list(columns.keys()):
            items = columns[col]
            barycenters: Dict[Tuple[str,str,str], float] = {}
            for g in items:
                neigh_cols = []
                for nb in adj.get(g, []):
                    nb_col = group_column.get(nb)
                    if nb_col is not None:
                        neigh_cols.append(col_pos_map.get(nb_col, col_pos_map.get(nb_col, 0)))
                if neigh_cols:
                    barycenters[g] = sum(neigh_cols) / len(neigh_cols)
                else:
                    barycenters[g] = col_pos_map.get(col, 0)
            items.sort(key=lambda g: (barycenters.get(g, 0), -len(adj.get(g, [])), g))
            columns[col] = items

        # 初始列 x 坐标（根据优化后 col_order）
        columns_x: Dict[int, int] = {}
        for idx, col in enumerate(col_order):
            columns_x[col] = group_x + idx * (group_width + group_gap)

        # 根据初始 columns_x 计算 group_positions 的 x,y，然后检测 Cabinet 之间水平重叠，
        # 若重叠则把后续列整体右移以消除重叠（迭代处理，保证柜体之间保留最小间隔）
        group_positions = {}
        vertical_gap = max(16, group_gap // 2)
        # 先生成初始 positions（不考虑 cabinet 容器）
        for col in col_order:
            cur_y = group_y_top
            for gkey in columns[col]:
                x = columns_x[col]
                group_positions[gkey] = (x, cur_y)
                cur_y += group_heights[gkey] + vertical_gap

        # -----------------------------
        # 柜内布局优化（左右两列：左侧放 FRONT_PANEL，右侧放其它）
        # -----------------------------
        # 按 cabinet 收集组
        cab_groups: Dict[str, List[Tuple[str,str,str]]] = {}
        for gkey in list(group_positions.keys()):
            cab = gkey[1] or ""
            cab_groups.setdefault(cab, []).append(gkey)

        for cab, gkeys in cab_groups.items():
            if not cab or len(gkeys) <= 1:
                continue
            # 分左右列
            left_groups = [g for g in gkeys if g[0] == "PANEL"]
            right_groups = [g for g in gkeys if g[0] != "PANEL"]

            # 构建柜内邻接关系，仅考虑属于同 cabinet 的组
            intra_adj: Dict[Tuple[str,str,str], Set[Tuple[str,str,str]]] = {g: set() for g in gkeys}
            for key in self.edges.keys():
                a_str, b_str = self.repr_map[key]
                g_a = node_to_group.get(a_str)
                g_b = node_to_group.get(b_str)
                if g_a in intra_adj and g_b in intra_adj and g_a != g_b:
                    intra_adj[g_a].add(g_b)
                    intra_adj[g_b].add(g_a)

            # 重心（基于当前 y 位置）用于排序
            def barycenter(g):
                neigh = intra_adj.get(g, ())
                if not neigh:
                    return group_positions[g][1]
                vals = [group_positions[n][1] for n in neigh if n in group_positions]
                return sum(vals) / len(vals) if vals else group_positions[g][1]

            left_groups.sort(key=lambda g: (barycenter(g), -len(intra_adj.get(g, [])), g))
            right_groups.sort(key=lambda g: (barycenter(g), -len(intra_adj.get(g, [])), g))

            # 计算两列的 x 偏移（以当前 cabinet 内最左 x 为基准）
            xs = [group_positions[g][0] for g in gkeys]
            minx = min(xs)
            left_x = minx
            inner_gap = max(12, group_gap // 4)
            right_x = left_x + group_width + inner_gap

            # 垂直对齐：按行放置左右两列，同一行高度取两者最大值
            max_rows = max(len(left_groups), len(right_groups))
            start_y = min(group_positions[g][1] for g in gkeys)
            cur_y = start_y
            for i in range(max_rows):
                gL = left_groups[i] if i < len(left_groups) else None
                gR = right_groups[i] if i < len(right_groups) else None
                hL = group_heights[gL] if gL else 0
                hR = group_heights[gR] if gR else 0
                row_h = max(hL, hR, node_height)
                if gL:
                    group_positions[gL] = (left_x, cur_y)
                if gR:
                    group_positions[gR] = (right_x, cur_y)
                cur_y += row_h + vertical_gap

        # 重新计算 cabinet_boxes 基于优化后的 group_positions（后续使用）
        # 注意：后面代码会再次计算 cabinet_boxes，但这里提前更新以减少后续重叠处理
        # （如果后续逻辑有基于旧 positions 的操作，请保留一致）
        # -----------------------------

        # 计算 cabinet_boxes（基于初始 group_positions）
        def compute_cabinet_boxes(positions: Dict[Tuple[str,str,str], Tuple[int,int]]) -> Dict[str, Tuple[int,int,int,int]]:
            boxes = {}
            for gkey, (gx, gy) in positions.items():
                cab = gkey[1] or ""
                if not cab:
                    continue
                gh = group_heights[gkey]
                minx, miny = gx, gy
                maxx, maxy = gx + group_width, gy + gh
                if cab in boxes:
                    ox1, oy1, ox2, oy2 = boxes[cab]
                    boxes[cab] = (min(minx, ox1), min(miny, oy1), max(maxx, ox2), max(maxy, oy2))
                else:
                    boxes[cab] = (minx, miny, maxx, maxy)
            return boxes

        # 基于列 x 坐标对柜体外框做水平分离，避免柜体重叠
        cabinet_boxes = compute_cabinet_boxes(group_positions)
        min_cab_gap = max(24, group_gap // 2)

        # 按左侧 x 排序的 cabinet 列表
        cab_items = sorted(cabinet_boxes.items(), key=lambda kv: kv[1][0])
        # 逐个检查并右移后续列以消除重叠（只调整 columns_x）
        # 注意：对 columns_x 使用 list(...) 遍历以避免迭代时修改 dict 导致问题
        for cab_id, (minx, miny, maxx, maxy) in cab_items:
            # 重新计算当前 cabinet_boxes（因为上次可能已被修改）
            cabinet_boxes = compute_cabinet_boxes(group_positions)
            # 找到最靠近且位于当前 cabinet 左侧的最大 right
            left_neighbors = [(k, v) for k, v in cabinet_boxes.items() if v[2] < minx]
            prev_max = max((v[2] for _, v in left_neighbors), default=-10**9)
            target_minx = prev_max + min_cab_gap if prev_max > -10**8 else minx
            if minx < target_minx:
                need = target_minx - minx
                # 对所有列 whose x >= minx 的列右移 need
                for col, x in list(columns_x.items()):
                    if x >= minx:
                        columns_x[col] = x + need
                # 更新 group_positions 基于新的 columns_x
                for col in col_order:
                    cur_y = group_y_top
                    for gkey in columns[col]:
                        x = columns_x[col]
                        group_positions[gkey] = (x, cur_y)
                        cur_y += group_heights[gkey] + vertical_gap
                # 重新计算 cabinet_boxes 用于后续判断
                cabinet_boxes = compute_cabinet_boxes(group_positions)

        # 最终确保 group_positions 与 columns_x 保持一致（如果没有变动，上面也会生成）
        for col in col_order:
            cur_y = group_y_top
            for gkey in columns[col]:
                x = columns_x[col]
                group_positions[gkey] = (x, cur_y)
                cur_y += group_heights[gkey] + vertical_gap

        # 为每个 Cabinet 计算包含所有其组的外框（用于绘制大方框容器）
        cabinet_boxes: Dict[str, Tuple[int,int,int,int]] = {}  # cabinet_id -> (minx,miny,maxx,maxy)
        for gkey, (gx, gy) in group_positions.items():
            cab_id = gkey[1] or ""
            if not cab_id:
                continue
            gw = group_width
            gh = group_heights[gkey]
            minx, miny = gx, gy
            maxx, maxy = gx + gw, gy + gh
            if cab_id in cabinet_boxes:
                ox1, oy1, ox2, oy2 = cabinet_boxes[cab_id]
                cabinet_boxes[cab_id] = (min(minx, ox1), min(miny, oy1), max(maxx, ox2), max(maxy, oy2))
            else:
                cabinet_boxes[cab_id] = (minx, miny, maxx, maxy)

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

        # 不再绘制机柜外框（去掉大方框），仅保留用于标注的 cabinet id 映射占位（空）
        # 组仍按计算好的绝对坐标放置在主画布上，稍后会在每个组标签中显示机柜名以便区分
        cabinet_cell_ids: Dict[str, str] = {}
        cabinet_padding = 0


        for gkey, nodes in sorted_groups:
            # 使用预先计算好的绝对位置（x,y）放置最外层组容器（始终放在根 parent="1"）
            pos = group_positions.get(gkey, (group_x, group_y_top))
            x_col, group_top_y = pos
            gid = gen_id()
            group_cell_ids[gkey] = gid
            # 在组标签中加入机柜名，便于区分
            cab_name = gkey[1] or ""
            g_label = f"{cab_name} | {gkey[0]}:{gkey[2] or gkey[1]}"
            group_style = "rounded=1;strokeColor=#444444;fillColor=#f5f5f5;"
            group_cell = ET.SubElement(root, "mxCell", id=gid, value="", style=group_style, vertex="1", parent="1")

            # layout: 为标签和节点留出空间 (与上面计算保持一致)
            # Use pre-calculated group_height to ensure consistency
            group_height = group_heights[gkey]
            # Calculate inner_nodes_height from group_height for use in component drawing
            inner_nodes_height = group_height - top_padding - label_height - between_label_and_nodes - bottom_padding
            ET.SubElement(group_cell, "mxGeometry", attrib={"x": str(x_col), "y": str(group_top_y), "width": str(group_width), "height": str(group_height), "as": "geometry"})

            # label cell：放在容器内顶部，明显可见，不会被节点遮挡（y 坐标相对于组容器）
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
            
            # 如果这是 DEVICE 组且有布局信息，则按矩阵方式绘制端子
            if gkey[0] == "DEVICE" and device_group_layouts:
                device_cabinet = gkey[1]
                device_group_id = gkey[2]
                layout_key = (device_cabinet, device_group_id)
                layout = device_group_layouts.get(layout_key)
                
                if layout:
                    # 使用矩阵布局绘制
                    start_x = x_col + 12
                    start_y = group_y_top + top_padding + label_height + between_label_and_nodes
                    
                    # 计算列数和每列宽度
                    max_cols = max(len(row) for row in layout) if layout else 1
                    col_width = max(40, (group_width - 24) // max_cols)
                    
                    for row_idx, row in enumerate(layout):
                        for col_idx, terminal_str in enumerate(row):
                            if terminal_str is None or not terminal_str:
                                # 空单元格，跳过
                                continue
                            
                            # 计算位置
                            nx = start_x + col_idx * col_width
                            ny = start_y + row_idx * (node_height + node_gap)
                            
                            # 绘制圆形节点
                            circle_id = gen_id()
                            node_cell_ids[terminal_str] = circle_id
                            circle_style = "shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000"
                            circle_cell = ET.SubElement(root, "mxCell", id=circle_id, value="", style=circle_style, vertex="1", parent=gid)
                            circle_size = max(4, node_height // 4)
                            ET.SubElement(circle_cell, "mxGeometry", attrib={
                                "x": str(nx - x_col),
                                "y": str(ny - group_y_top + (node_height - circle_size)//2),
                                "width": str(circle_size),
                                "height": str(circle_size),
                                "as": "geometry"
                            })
                            
                            # 绘制文本标签
                            label = terminal_str.split(":")[-1]
                            text_id = gen_id()
                            text_style = "text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none"
                            text_cell = ET.SubElement(root, "mxCell", id=text_id, value=escape(label), style=text_style, vertex="1", parent=gid)
                            ET.SubElement(text_cell, "mxGeometry", attrib={
                                "x": str((nx - x_col) + circle_size + 6),
                                "y": str(ny - group_y_top),
                                "width": str(max(10, col_width - circle_size - 12)),
                                "height": str(node_height),
                                "as": "geometry"
                            })
                    # 跳过默认的端子绘制
                    continue
            
            # 如果这是 COMPONENT 组，则不绘制组内各个端子，而是绘制一个表示整个 component 的块，
            # 并把组内所有端子映射到该块的 cell id（外部连线直接连到块）
            if gkey[0] == "COMPONENT":
                # 在组内放一个代表组件的块（宽度留内边距），高度使用组内节点高度（inner_nodes_height）
                comp_block_id = gen_id()
                # 尝试用提供的 component_types 映射显示元件类型；否则回退为 component_id
                comp_cabinet = gkey[1]
                comp_id = gkey[2] or ""
                # 优先使用已知图形映射（COMPONENT_GRAPHICS），否则绘制文字块
                comp_type_str = None
                if component_types:
                    comp_type_str = component_types.get((comp_cabinet, comp_id))
                # 允许直接用 component_id 作为回退类型名
                comp_type_str = comp_type_str or comp_id or ""

                comp_x = x_col + 12
                comp_y = group_y_top + top_padding + label_height + between_label_and_nodes
                comp_w = max(40, group_width - 24)
                comp_h = max(node_height, inner_nodes_height)

                gfx = COMPONENT_GRAPHICS.get(comp_type_str)
                if gfx:
                    # 使用预定义图形（保持 parent=gid，以便放在组内）
                    comp_cell = ET.SubElement(root, "mxCell", id=comp_block_id, value=gfx.get("value", ""),
                                              style=gfx.get("style", ""), vertex="1", parent=gid)
                    g_w = int(gfx.get("width", comp_w))
                    g_h = int(gfx.get("height", comp_h))
                    # 居中放置在组可用宽度内（左内边距为 12）
                    ET.SubElement(comp_cell, "mxGeometry", attrib={
                        "x": str(comp_x - x_col + max(0, (comp_w - g_w)//2)),
                        "y": str(comp_y - group_y_top + max(0, (comp_h - g_h)//2)),
                        "width": str(g_w),
                        "height": str(g_h),
                        "as": "geometry"
                    })
                else:
                    # 回退为文字标签的矩形块
                    comp_label = comp_type_str or "COMPONENT"
                    comp_style = "shape=rectangle;rounded=1;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;fillColor=#E8F0FE;strokeColor=#1A73E8"
                    comp_cell = ET.SubElement(root, "mxCell", id=comp_block_id, value=escape(comp_label), style=comp_style, vertex="1", parent=gid)
                    ET.SubElement(comp_cell, "mxGeometry", attrib={
                        "x": str(comp_x - x_col),
                        "y": str(comp_y - group_y_top),
                        "width": str(comp_w),
                        "height": str(comp_h),
                        "as": "geometry"
                    })
                # 把组内所有端子指向这个块 id（边会连接到该块）
                for nstr in ordered_nodes:
                    node_cell_ids[nstr] = comp_block_id
                # 跳过逐端子绘制
                continue

            for ni, nstr in enumerate(ordered_nodes):
                nx = x_col + 12
                ny = group_y_top + top_padding + label_height + between_label_and_nodes + ni * (node_height + node_gap)
                # 使用较小的圆形节点 (当前尺寸的 1/4) + 旁边的文本标签
                label = nstr.split(":")[-1]
                circle_id = gen_id()
                node_cell_ids[nstr] = circle_id  # 边连接指向圆形节点 id
                circle_style = "shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000"
                circle_cell = ET.SubElement(root, "mxCell", id=circle_id, value="", style=circle_style, vertex="1", parent=gid)
                # 圆的大小取 node_height 的 1/4，至少为 4 像素以保证可见
                circle_size = max(4, node_height // 4)
                ET.SubElement(circle_cell, "mxGeometry", attrib={
                    "x": str(nx - x_col),
                    "y": str(ny - group_y_top + (node_height - circle_size)//2),  # 垂直居中于原高度行
                    "width": str(circle_size),
                    "height": str(circle_size),
                    "as": "geometry"
                })
                # 文本标签放在圆的右侧
                text_id = gen_id()
                text_style = "text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none"
                text_cell = ET.SubElement(root, "mxCell", id=text_id, value=escape(label), style=text_style, vertex="1", parent=gid)
                ET.SubElement(text_cell, "mxGeometry", attrib={
                    "x": str((nx - x_col) + circle_size + 6),
                    "y": str(ny - group_y_top),
                    "width": str(max(10, node_width - circle_size - 12)),
                    "height": str(node_height),
                    "as": "geometry"
                })

        # 为每个 GLOBAL_WIRE 创建一个单独的中转节点（不放入任何容器）
        wire_base_x = group_x + max(1, len(sorted_groups)) * (group_width + group_gap) + 40
        wire_index = 0
        for w in sorted(wire_nodes):
            # 解析显示标签
            m = re.match(r"@GLOBAL_WIRE:([^:]*):(.*)", w)
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
                # 使用较小的圆形表示端子 (当前尺寸的 1/4)，文本放在右侧
                circle_id = gen_id()
                node_cell_ids[a_str] = circle_id
                standalone_index += 1
                cx = 40
                cy = 40 + standalone_index * (node_height + node_gap)
                circle_size = max(4, node_height // 4)
                circle_cell = ET.SubElement(root, "mxCell", id=circle_id, value="",
                                            style="shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000",
                                            parent="1", vertex="1")
                ET.SubElement(circle_cell, "mxGeometry", attrib={"x": str(cx), "y": str(cy + (node_height - circle_size)//2), "width": str(circle_size), "height": str(circle_size), "as": "geometry"})
                text_id = gen_id()
                text_cell = ET.SubElement(root, "mxCell", id=text_id, value=escape(a_str),
                                          style="text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none",
                                          parent="1", vertex="1")
                ET.SubElement(text_cell, "mxGeometry", attrib={"x": str(cx + circle_size + 6), "y": str(cy), "width": str(max(10, node_width - circle_size - 12)), "height": str(node_height), "as": "geometry"})

            if b_str not in node_cell_ids:
                node_cell_ids[b_str] = circle_id
                standalone_index += 1
                cx = 160
                cy = 40 + standalone_index * (node_height + node_gap)
                circle_size = max(4, node_height // 4)
                circle_cell = ET.SubElement(root, "mxCell", id=circle_id, value="",
                                            style="shape=ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000",
                                            parent="1", vertex="1")
                ET.SubElement(circle_cell, "mxGeometry", attrib={"x": str(cx), "y": str(cy + (node_height - circle_size)//2), "width": str(circle_size), "height": str(circle_size), "as": "geometry"})
                text_id = gen_id()
                text_cell = ET.SubElement(root, "mxCell", id=text_id, value=escape(b_str),
                                          style="text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none",
                                          parent="1", vertex="1")
                ET.SubElement(text_cell, "mxGeometry", attrib={"x": str(cx + circle_size + 6), "y": str(cy), "width": str(max(10, node_width - circle_size - 12)), "height": str(node_height), "as": "geometry"})

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
            elif "元件编号" in df.columns and "元件类型" in df.columns:
                self._process_backend_components_dataframe(df, description=f"{file_path} - {sheet_name}")

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
                    # Try to find device_group_id from existing device groups
                    device_group_id = None
                    for dgid, dginfo in cabinet.backend_device_groups.items():
                        for tref in dginfo.terminal_refs:
                            if tref.terminal_name == ic:
                                device_group_id = dgid
                                break
                        if device_group_id:
                            break
                    
                    ic_terminal_ref = TerminalRef(
                        cabinet_id=cabinet_id,
                        device_group_id=device_group_id,
                        terminal_name=ic,
                        terminal_type=TerminalType.BACKEND_DEVICE
                    )
                    internal_connection_terminal_refs.append(ic_terminal_ref)

            terminal_info.internal_connection_terminal_refs = internal_connection_terminal_refs

            cable_id = TerminalDataModel.safe_str(row.get("电缆编号", ""))
            loop_number = TerminalDataModel.safe_str(row.get("回路号", ""))
            if not cable_id:
                logger.warning(f"{description}:{index}: 警告: 端子 {terminal_ref} 的电缆编号为空，将此处判定断开。")
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
                    return TerminalRef(
                        cabinet_id=cabinet_id,
                        component_id=id_part,
                        terminal_name=name_part,
                        terminal_type=TerminalType.BACKEND_COMPONENT
                    )
                else:
                    # Try to find device_group_id from existing device groups
                    device_group_id = None
                    for dgid, dginfo in cabinet.backend_device_groups.items():
                        for tref in dginfo.terminal_refs:
                            if tref.terminal_name == terminal_str:
                                device_group_id = dgid
                                break
                        if device_group_id:
                            break
                    
                    return TerminalRef(
                        cabinet_id=cabinet_id,
                        device_group_id=device_group_id,
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
        每行代表该装置组的一行布局，布局端子内以 ';' 分隔同一行内的端子。
        空单元格用空字符串表示（连续分号或开头分号）。
        例如:
          1n1x1;1n1x2  -> 第一行两列
          1n1x3;1n1x4  -> 第二行两列
          
          1n1x1;1n1x2  -> 第一行两列
          ;1n1x3       -> 第二行第一列空，第二列有端子
          ;1n1x4       -> 第三行第一列空，第二列有端子
          
            设备编号	装置编号	装置组编号	布局端子
            1ABA03GG003	61LH	61LH	61LHa;61LHb
            1ABA03GG003	61LH	61LH	61LHc;61LHn
            1ABA01GG003	42LH	42LH1	42LHa
            1ABA01GG003	42LH	42LH1	42LHb
            1ABA01GG003	42LH	42LH2	42LHc
            1ABA01GG003	42LH	42LH2	42LHn
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
            
            if not device_group_id:
                logger.warning(f"{description}:{index}: 装置组编号为空，使用装置编号或跳过。")
                continue

            # 创建或取出 BackendDeviceGroupInfo
            dg_info = cabinet.backend_device_groups.get(device_group_id)
            if not dg_info:
                dg_info = BackendDeviceGroupInfo()
                dg_info.device_id = device_id
                dg_info.device_group_id = device_group_id
                dg_info.terminal_refs = []
                dg_info.terminal_layout = []  # 初始化2D布局
                cabinet.backend_device_groups[device_group_id] = dg_info

            # 解析一行布局端子，以分号分隔，保留空单元格
            # 使用split而不是split_to_list，以保留空字符串
            terminal_names_in_row = layout_terminals_raw.split(';')
            row_refs = []
            for tn in terminal_names_in_row:
                tn = tn.strip()
                if tn:
                    tref = TerminalRef(
                        cabinet_id=cabinet_id,
                        device_group_id=device_group_id,
                        terminal_name=tn,
                        terminal_type=TerminalType.BACKEND_DEVICE
                    )
                    row_refs.append(tref)
                    dg_info.terminal_refs.append(tref)  # 同时保留在flat list中以兼容现有代码
                else:
                    # 空单元格
                    row_refs.append(None)
            
            # 添加这一行到2D布局
            if row_refs:  # 只有在有内容时才添加行
                dg_info.terminal_layout.append(row_refs)
                
            logger.debug(f"{description}:{index}: 读取柜 {cabinet_id} 装置组 {device_group_id} 布局端子行: {[tn for tn in terminal_names_in_row]}")


    def _process_backend_components_dataframe(self, df: pd.DataFrame, description: str =""):
        """
            设备编号	元件编号	元件类型	元件端子
            1ABA03GG003	1DK	刀开关	1DK:2;1DK:1
        """
        for index, row in df.iterrows():
            cabinet_id = TerminalDataModel.safe_str(row.get("设备编号", ""))
            if not cabinet_id:
                logger.warning(f"{description}:{index}: 未找到设备编号，跳过该行。")
                continue
            cabinet = next((c for c in self.cabinets if c.id == cabinet_id), None)
            if not cabinet:
                cabinet = Cabinet(id=cabinet_id)
                self.cabinets.append(cabinet)

            component_id = TerminalDataModel.safe_str(row.get("元件编号", ""))
            component_type = TerminalDataModel.safe_str(row.get("元件类型", ""))
            terminals_raw = TerminalDataModel.safe_str(row.get("元件端子", ""))
            terminal_names = TerminalDataModel.split_to_list(terminals_raw)

            if not component_id:
                logger.warning(f"{description}:{index}: 元件编号为空，跳过该行。")
                continue

            # 如果已有相同 component_id，记录并覆盖（或可改为合并）
            if component_id in cabinet.backend_components:
                logger.info(f"{description}:{index}: 元件 {component_id} 在机柜 {cabinet_id} 已存在，更新信息。")

            info = BackendComponentInfo()
            info.component_id = component_id
            info.component_type = component_type
            info.terminal_refs = [
                TerminalRef(
                    cabinet_id=cabinet_id,
                    component_id=component_id,
                    terminal_name= tn.split(':')[-1],  # 仅保留端子名部分
                    terminal_type=TerminalType.BACKEND_COMPONENT
                ) for tn in terminal_names
            ]

            cabinet.backend_components[component_id] = info
            logger.debug(f"{description}:{index}: 读取元件 {component_id} (type={component_type}) 包含端子: {terminal_names}")


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
            for component_id, component_info in cabinet.backend_components.items():
                print(f"  Backend Component ID: {component_id}, Type: {component_info.component_type}, Terminals: {component_info.terminal_refs}")
            for backend_connection in cabinet.backend_connections:
                print(f"  Backend Connection: From {backend_connection.from_terminal} To {backend_connection.to_terminal}")
            for dgid, dginfo in cabinet.backend_device_groups.items():
                print(f"  Backend Device Group ID: {dgid}, Device ID: {dginfo.device_id}, Terminals: {dginfo.terminal_refs}")

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
                        # 仅当电缆编号存在时才认为属于同一 GlobalWire，从而建立到全局线的连边
                        gw = terminal_info.external_connection_wire
                        if getattr(gw, "cable_id", None):
                            graph.add_edge(terminal_ref, gw, "external_wire")
                        else:
                            # 如果只有回路号但无电缆编号，则不认为与其他相同回路号节点相连
                            # 不创建到 GLOBAL_WIRE 的边，避免把仅有回路号的端子错误合并
                            pass
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
            # 从 cabinet.backend_device_groups 中收集 device_group terminals
            for dgid, dginfo in cabinet.backend_device_groups.items():
                key = (cabinet.id, dgid)
                lst = terminals_by_device_group.setdefault(key, [])
                for tref in getattr(dginfo, "terminal_refs", []):
                    lst.append(tref)


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
        # 过滤：避免导出“空白”图纸
        # - 跳过没有任何实际边且节点数 <= 1 的子图（通常是孤立单节点或无意义的空组）
        # - 如果需要更严格的过滤规则，可在此处扩展（例如排除仅包含 GLOBAL_WIRE 的组等）
        filtered_groups: List[ConnectionGraph] = []
        for g in groups:
            has_edges = bool(g.edges)
            node_count = len(g.nodes)
            if not has_edges and node_count <= 1:
                logger.info(f"跳过空白子图：nodes={node_count}, edges={len(g.edges)}")
                continue
            filtered_groups.append(g)

        if not filtered_groups:
            logger.info("没有可导出的子图（所有子图被过滤）。")
            return []

        out_paths = []
        for i, g in enumerate(filtered_groups, start=1):
            tb_ids = set()
            dg_ids = set()
            comp_ids = set()
            gw_ids = set()
            for node in g.nodes:
                m = re.match(r"[^/]+/@PANEL:([^:]+):", node)
                if m:
                    tb_ids.add(m.group(1))
                    continue
                m = re.match(r"[^/]+/@DEVICE:([^']+)'", node)
                if m:
                    dg_ids.add(m.group(1))
                    continue
                m = re.match(r"[^/]+/@COMPONENT:([^:]+):", node)
                if m:
                    comp_ids.add(m.group(1))
                    continue
                m = re.match(r"@GLOBAL_WIRE:([^:]*):(.*)", node)
                if m:
                    gw_ids.add(f"{m.group(1)}/{m.group(2)}")
                    print("found global wire " + m.group(1) + "/" + m.group(2))
                    continue

            parts = []
            if tb_ids:
                parts.append("TB:" + ",".join(sorted(tb_ids)))
            if dg_ids:
                parts.append("DG:" + ",".join(sorted(dg_ids)))
            if comp_ids:
                parts.append("CMP:" + ",".join(sorted(comp_ids)))
            if gw_ids:
                parts.append("GW:" + ",".join(sorted(gw_ids)))
            if not dg_ids and not comp_ids and not gw_ids:
                parts.append("SEQ:" + str(i))
            title = " | ".join(parts) if parts else f"Group {i}"

            # sanitize filename (移除/替换不安全字符)
            fname_base = re.sub(r'[\\/:*?"<>|\s]+', '_', title)
            if not fname_base:
                fname_base = f"group_{i}"
            # 避免名称过长
            if len(fname_base) > 100:
                fname_base = fname_base[:100]
            fp = os.path.join(out_folder, f"{fname_base}.drawio")
            if out_paths.count(fp):
                fp = os.path.join(out_folder, f"{fname_base}_{i}.drawio")

            # 构建 component_type 映射 (cabinet_id, component_id) -> component_type
            comp_map: Dict[Tuple[str,str], str] = {}
            for cabinet in self.cabinets:
                for cid, info in cabinet.backend_components.items():
                    comp_map[(cabinet.id, cid)] = getattr(info, "component_type", "") or ""
            
            # 构建 device_group_layout 映射 (cabinet_id, device_group_id) -> List[List[Optional[str]]]
            # 将 TerminalRef 转换为字符串以便在绘图代码中使用
            dg_layout_map: Dict[Tuple[str,str], List[List[Optional[str]]]] = {}
            for cabinet in self.cabinets:
                for dgid, dginfo in cabinet.backend_device_groups.items():
                    layout = getattr(dginfo, "terminal_layout", None)
                    if layout:
                        # 转换 TerminalRef 为字符串
                        str_layout = []
                        for row in layout:
                            str_row = [str(tref) if tref else None for tref in row]
                            str_layout.append(str_row)
                        dg_layout_map[(cabinet.id, dgid)] = str_layout

            g.to_drawio_xml(fp, title=title, component_types=comp_map, device_group_layouts=dg_layout_map)
            out_paths.append(fp)
        return out_paths

if __name__ == "__main__":
    # 示例用法
    # excel_fold_path = r"C:\Users\OhtoAi\Downloads\继电保护室保护图纸 解析成果"
    # excel_fold_path = r"C:\Users\OhtoAi\Downloads\小测试"
    excel_fold_path = r"C:/Users/OhtoAi/Downloads/母线保护"
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
