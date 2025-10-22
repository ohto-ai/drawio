import pandas as pd
from typing import List, Optional, Dict, Any, Set, Iterable
from dataclasses import dataclass
from enum import Enum
import re
from pathlib import Path
from collections import deque, defaultdict
from xml.sax.saxutils import escape

@dataclass
class TerminalInfo:
    """端子排信息数据类"""
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

class TerminalBlockReader:
    """端子排信息读取器"""
    
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
    注意：
      - 回路号在图中作为连线的标签（value），而不是独立节点。
      - 节点仍以三元组 (cabinet, block, terminal) 表示，避免 '/' 冲突。
      - 导出时会把端子按机柜/端子排分组，端子排内按表格布局排列，端子之间的连线会被绘制并在必要时显示回路号。
    """
    CIRCUIT_PREFIX = "@CIRCUIT:"
    INTERNAL_PREFIX = "@INTERNAL:"
    
    def __init__(self):
        # 邻接表：键为节点（tuple 或 circuit/internal string），值为相邻节点集合
        self.adj: Dict[Any, Set[Any]] = defaultdict(set)
        # 记录所有终端节点对应的 TerminalInfo，键为三元组 (cabinet, block, terminal)
        self.terminal_info_map: Dict[tuple, TerminalInfo] = {}
        # 记录边集合，用 frozenset({a,b}) 保证无向边唯一（a/b 可以是 tuple 或 string）
        self.edges: Set[frozenset] = set()
        # 可选的边标签（frozenset({a,b}) -> str），用于标注来自回路表/柜内连接表的连接关系（如 开关/常闭开关）
        self.edge_labels: Dict[frozenset, str] = {}

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

    def _record_edge(self, a: Any, b: Any, label: Optional[str] = None):
        """内部：记录无向边为 frozenset，以保证唯一性；可附带边标签（不一定覆盖已有回路标签）"""
        if a is None or b is None:
            return
        if a == "" or b == "":
            return
        key = frozenset({a, b})
        self.edges.add(key)
        if label and label.strip():
            # 只在没有标签或存在时用后者覆盖（保守策略：如果已有标签与回路/内部标签冲突，导出阶段会按优先级处理）
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
        返回节点（三元组）或 None（解析失败）。注意：对于仅端子号，返回 (default_cab, default_blk, terminal)。
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

        # 处理 internal_wiring：尝试把 internal 名称解析为端子（三元组）；若解析成功则把那个端子作为普通端子处理并连线，
        # 否则退回到旧的字符串 internal 节点（保持兼容旧数据格式）
        for internal in terminal.internal_wiring:
            if not internal:
                continue
            # first try parsing as a terminal-like name (supports "Cabinet/Block:Terminal", "Block:Terminal", "Terminal")
            parsed = self._parse_interconnect(internal, terminal.cabinet_name, terminal.terminal_block)
            if parsed:
                # ensure parsed node exists in adj (if actual TerminalInfo present, it'll already be there after build_from_terminals)
                _ = self.adj[parsed]
                self.add_edge(node, parsed)
            else:
                # fallback: keep legacy internal string node
                inode = self.make_internal_node(internal)
                self.add_edge(node, inode)

        return node

    def build_from_terminals(self, terminals: Iterable[TerminalInfo]):
        # 清空已有图
        self.adj.clear()
        self.terminal_info_map.clear()
        self.edges.clear()
        self.edge_labels.clear()
        # 先加入所有端子节点（以便互联引用不存在时也能查询到节点）
        for t in terminals:
            node = self.make_terminal_node(t.cabinet_name, t.terminal_block, t.terminal_number)
            self.terminal_info_map[node] = t
            _ = self.adj[node]

        # 再添加实际边
        for t in terminals:
            self.add_terminal(t)

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
        """
        接受 "Cabinet/Block:Terminal" 或 "Block:Terminal" 或 "Terminal" 等格式字符串
        """
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
            # 使用可读字符串作为键
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
                # 保持可读顺序
                res.append((a_str, b_str))
        return res

    def summarize_component(self, comp: Set[Any]) -> Dict[str, Any]:
        """把组件转成可序列化的摘要结构，包含节点和边信息（用于拓扑绘制）"""
        terminals = [n for n in comp if isinstance(n, tuple)]
        circuits = [n[len(self.CIRCUIT_PREFIX):] for n in comp if isinstance(n, str) and n.startswith(self.CIRCUIT_PREFIX)]
        # internal wiring 名称（合并来自字符串 internal 节点与各端子的 internal_wiring 字段）
        internals_set = set()
        for n in comp:
            if isinstance(n, str) and not n.startswith(self.CIRCUIT_PREFIX):
                if n.startswith(self.INTERNAL_PREFIX):
                    internals_set.add(n[len(self.INTERNAL_PREFIX):])
                else:
                    internals_set.add(n)
        # 也从每个端子的 TerminalInfo.internal_wiring 收集名称
        for t in terminals:
            info = self.terminal_info_map.get(t)
            if info:
                for name in info.internal_wiring:
                    if name:
                        internals_set.add(name)
        internals = sorted(internals_set)
        edges = self.get_component_edges(comp)
        adj = self.get_component_subgraph_adj(comp)
        # 附带每个终端的 TerminalInfo（若存在）
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
        读取一个文件夹中所有回路表（Excel），只处理名为或包含 '柜内端子连接' 的 sheet。
        每行关注 '端子号' 和 '互联端子号'，以及可选 '连接关系'（为空/开关/常闭开关等）。
        名称可以是全局端子号（例如 1n1x4），也可以是带块名或柜名的形式。
        将根据这些信息在图中添加边或标注边类型（将作为边标签保存在 edge_labels）。
        """
        p = Path(dir_path)
        if not p.exists():
            print(f"连接表目录不存在: {dir_path}")
            return

        # helper: 用已有 terminal_info_map 查找与给定名称匹配的节点集合
        def resolve_name_to_nodes(name: str) -> List[Any]:
            name = (name or "").strip()
            if not name:
                return []
            # 拆分复合（如果传入多个在一格的情况，调用者应先拆分）
            # 解析是否含有 ':' 或 '/'
            if ":" in name or "/" in name:
                parsed = self._parse_interconnect(name, None, None)
                if not parsed:
                    return []
                cab_p, blk_p, ter_p = parsed
                res = []
                for node in self.terminal_info_map.keys():
                    # node: (cab, blk, ter)
                    match = True
                    if ter_p and node[2] != ter_p:
                        match = False
                    if cab_p and cab_p != "" and node[0] != cab_p:
                        match = False
                    if blk_p and blk_p != "" and node[1] != blk_p:
                        match = False
                    if match:
                        res.append(node)
                return res
            else:
                # 仅端子号：全局匹配 terminal_number 字段相等的所有端子
                res = [n for n in self.terminal_info_map.keys() if n[2] == name]
                return res

        # 分割多值的简单函数（支持 ; , 中文分号逗号和空格）
        def split_multi(value: str) -> List[str]:
            if not value:
                return []
            parts = re.split(r'[;,，；/]+', value)
            return [p.strip() for p in parts if p.strip()]

        # 遍历目录中的 Excel 文件
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
                # 规范列名
                df.columns = [str(c).strip() for c in df.columns]
                # 尝试寻找关键列名，宽松匹配
                col_map = {c: c for c in df.columns}
                # 必需列: 端子号, 互联端子号 (可能列名稍有差别)
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

                    # 若无法解析到任何真实端子节点，则跳过并打印警告
                    if not left_nodes or not right_nodes:
                        # 尝试宽松匹配：如果名字本身存在于 terminal_info_map 的 terminal_number 里但未找到，仍跳过
                        print(f"在 {file}:{sheet} 第 {idx+1} 行未解析到端子节点: 左 {left_raw} -> {left_nodes}, 右 {right_raw} -> {right_nodes}")
                        continue

                    # 为每对端子建立边，label 根据 relation（开关/常闭开关/空）
                    for a in left_nodes:
                        for b in right_nodes:
                            if a == b:
                                continue
                            lbl = relation if relation else None
                            # 把连接加入图中（若已有回路标签，导出阶段会以回路为优先）
                            self.add_edge(a, b, label=lbl)
                print(f"已处理连接表: {file} - {sheet}")

    def export_drawio_xml(self, comp: Set[Any], output_path: Path, title: str = "diagram"):
        """
        简化导出：仅绘制端子顶点（无机柜/端子排容器），并绘制端子间的连接。
        回路号处理：
          - 若某回路号关联多个端子（>2），则在这些端子之间绘制成完全连通（每对一条线），
            且在连线上标注回路号（回路号作为边的 label）。
          - internal_wiring 也会按名称在该名称关联的端子间生成完全连通（标签为 internal 名称），
            但不会覆盖已有的回路标签（回路标签优先）。
          - 同时保留由互联字段生成的直接边（若存在），标签为空或来源于共同回路号 / internal 名称 / 连接表标签。
        支持输出为 .drawio (mxfile XML) ，diagrams.net 可直接打开）。
        """
        if not comp:
            raise ValueError("组件为空，无法导出 drawio。")

        # 将要绘制的节点：排除回路节点，但包含字符串形式的 internal 节点（兼容旧格式）
        draw_nodes = [n for n in comp if not (isinstance(n, str) and n.startswith(self.CIRCUIT_PREFIX))]
        if not draw_nodes:
            raise ValueError("组件中无可绘制节点。")

        # 为字符串节点（internal 名称）生成用于布局的三元组表示：
        # 若字符串可以解析为端子（如 "Block:Terminal" 等），则使用解析结果；否则用 ('', name, '') 作为合成节点。
        layout_terms = []
        layout_map: Dict[Any, tuple] = {}
        for n in draw_nodes:
            if isinstance(n, tuple):
                layout_map[n] = n
                layout_terms.append(n)
            else:
                name = n
                # 去掉 INTERNAL_PREFIX（若存在）
                if name.startswith(self.INTERNAL_PREFIX):
                    name = name[len(self.INTERNAL_PREFIX):]
                # 尝试解析为端子三元组
                parsed = self._parse_interconnect(name, None, None)
                if parsed:
                    layout_map[n] = parsed
                    layout_terms.append(parsed)
                else:
                    synthetic = ("", name, "")
                    layout_map[n] = synthetic
                    layout_terms.append(synthetic)

        # 布局：按 block 列、纵向排列（使用合成/解析后的三元组）
        positions = self._layout_terminals_grid(layout_terms)

        # id 映射（基于原始节点：tuple 或 string）
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

        # 顶点：为所有 draw_nodes 绘制（包括解析/合成的 internal 节点）
        for node in sorted(draw_nodes, key=self._node_sort_key):
            cell_id = nid()
            id_map[node] = cell_id
            layout_node = layout_map.get(node)
            # label 优先使用原始字符串（去掉 INTERNAL_PREFIX），若为 tuple 则使用 make_terminal_id_str
            if isinstance(node, str):
                lab = node
                if lab.startswith(self.INTERNAL_PREFIX):
                    lab = lab[len(self.INTERNAL_PREFIX):]
                label = escape(lab)
            else:
                label = escape(self.make_terminal_id_str(layout_node))
            x, y, w, h = positions.get(layout_node, (40, 40, 120, 48))
            style = "shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000"
            cells.append(f'<mxCell id="{cell_id}" value="{label}" style="{style}" vertex="1" parent="1">')
            cells.append(f'  <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>')
            cells.append('</mxCell>')

        # 构造要绘制的边集合：使用集合避免重复
        edges_to_draw = {}  # (a,b) tuple(sorted) -> label (如果多条来源，优先回路号)
        # 1) 来自 self.edges 的直接边（只要两端都在 draw_nodes 中就绘制）
        for e in self.edges:
            if len(e) != 2:
                continue
            a, b = tuple(e)
            if a not in draw_nodes or b not in draw_nodes:
                continue
            key = tuple(sorted([a, b], key=self._node_sort_key))
            label = ""
            # 若两端都是实际端子且共享同一回路号，则以回路号为标签
            ai = self.terminal_info_map.get(a) if isinstance(a, tuple) else None
            bi = self.terminal_info_map.get(b) if isinstance(b, tuple) else None
            if ai and bi and ai.circuit_number and ai.circuit_number == bi.circuit_number:
                label = ai.circuit_number
            # 若没有回路标签，检查是否存在来自连接表/其它来源的边标签
            if not label:
                edge_key = frozenset({a, b})
                if edge_key in self.edge_labels:
                    label = self.edge_labels[edge_key]
            # 回路标签优先覆盖已有标签
            if key in edges_to_draw and edges_to_draw[key]:
                continue
            edges_to_draw[key] = label

        # 2) 对每个回路号，若包含多个端子，生成完全连通（每对标注回路号），并合并到 edges_to_draw（仅包含 draw_nodes）
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
                    edges_to_draw[key] = circ  # 回路号优先覆盖

        # 最终将 edges_to_draw 写入 cells（无向线）
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

        # 组装 mxGraphModel XML（mxfile）
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

        # 创建文件夹
        import os
        os.makedirs(output_path.parent, exist_ok=True)
        # 写入 mxfile (.drawio/.xml)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(mxgraph)
        print(f"已导出 drawio XML 到: {output_path}")

# 使用示例
if __name__ == "__main__":
    # 读取命令行参数
    # 创建读取器实例
    
    # 命令行参数解析
    import argparse
    # input_dir_path
    # --output_dir_path
    parser = argparse.ArgumentParser(description="读取端子排信息并构建连接图。")
    parser.add_argument("--term", type=str, help="包含端子排 Excel 文件的目录路径")
    parser.add_argument("--route", type=str, help="包含路由表 Excel 文件的目录路径")
    parser.add_argument("--output_dir_path", type=str, default="outputs", help="输出 drawio 文件的目录路径")
    # parser.add_argument("--format", type=str, default="drawio", choices=["drawio", "svg"], help="输出文件格式，drawio 或 svg")
    args = parser.parse_args()
    
    term_xlsx_dir_path = args.term
    route_xlsx_dir_path = args.route
    
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
    graph.load_connection_sheets(route_xlsx_dir_path)
    graph.build_from_terminals(terminal_blocks)

# import pprint
    import pprint
    # 根据回路查询组件
    # comp = graph.get_component_by_circuit("A4451")
    # pprint.pprint(graph.summarize_component(comp))
    # graph.export_drawio_xml(comp, Path("circuit_A4451.drawio"), title="Circuit A4451")
    
    # 导出所有回路组件的 drawio 文件, 没有回路号的不要导出, 端子少于2个的也不要导出
    all_comps = graph.get_all_components()
    for rep, comp in all_comps.items():
        # 检查组件中是否有回路节点
        has_circuit = any(isinstance(n, str) and n.startswith(ConnectionGraph.CIRCUIT_PREFIX) for n in comp)
        if not has_circuit:
            continue
        # 检查端子数量
        terminal_count = sum(1 for n in comp if isinstance(n, tuple))
        if terminal_count < 2:
            continue
        safe_rep = rep.replace("/", "_").replace(":", "_")
        output_file = Path(args.output_dir_path) / f"component_{safe_rep}.drawio"
        # if args.format == "drawio":
        #     output_file = Path(args.output_dir_path) / f"component_{safe_rep}.drawio"
        # else:
            # output_file = Path(args.output_dir_path) / f"component_{safe_rep}.drawio.svg"
        graph.export_drawio_xml(comp, output_file, title=f"Component {rep}")

