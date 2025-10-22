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

    def _record_edge(self, a: Any, b: Any):
        """内部：记录无向边为 frozenset，以保证唯一性"""
        if a is None or b is None:
            return
        if a == "" or b == "":
            return
        self.edges.add(frozenset({a, b}))

    def add_edge(self, a: Any, b: Any):
        """在邻接表中加入无向边并记录到 edges"""
        if not a or not b:
            return
        self.adj[a].add(b)
        self.adj[b].add(a)
        self._record_edge(a, b)

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

        # 处理 internal_wiring：把每个 internal 名称当作全局字符串节点加入（比如 "1DK" 或 "3DK:1"）
        # 并与当前端子建立边。这样同一 internal 名称连接的多个端子会被视为连通。
        for internal in terminal.internal_wiring:
            if not internal:
                continue
            inode = self.make_internal_node(internal)
            self.add_edge(node, inode)

        return node

    def build_from_terminals(self, terminals: Iterable[TerminalInfo]):
        # 清空已有图
        self.adj.clear()
        self.terminal_info_map.clear()
        self.edges.clear()
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
        # internal wiring 名称（去掉前缀）
        internals = [n[len(self.INTERNAL_PREFIX):] for n in comp if isinstance(n, str) and n.startswith(self.INTERNAL_PREFIX)]
        edges = self.get_component_edges(comp)
        adj = self.get_component_subgraph_adj(comp)
        # 附带每个终端的 TerminalInfo（若存在）
        terminal_infos = {self.make_terminal_id_str(n): self.terminal_info_map.get(n) for n in terminals}
        return {
            "terminals": sorted([self.make_terminal_id_str(n) for n in terminals]),
            "circuits": sorted(circuits),
            "internals": sorted(internals),
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

    def export_drawio_xml(self, comp: Set[Any], output_path: Path, title: str = "diagram"):
        """
        简化导出：仅绘制端子顶点（无机柜/端子排容器），并绘制端子间的连接。
        回路号处理：
          - 若某回路号关联多个端子（>2），则在这些端子之间绘制成完全连通（每对一条线），
            且在连线上标注回路号（回路号作为边的 label）。
          - internal_wiring 也会按名称在该名称关联的端子间生成完全连通（标签为 internal 名称），
            但不会覆盖已有的回路标签（回路标签优先）。
          - 同时保留由互联字段生成的直接边（若存在），标签为空或来源于共同回路号 / internal 名称。
        支持输出为 .drawio (mxfile XML) ，diagrams.net 可直接打开）。
        """
        if not comp:
            raise ValueError("组件为空，无法导出 drawio。")

        # 仅保留端子节点
        terminals = [n for n in comp if isinstance(n, tuple)]
        if not terminals:
            raise ValueError("组件中无终端节点可绘制。")

        # 布局：按 block 列、纵向排列
        positions = self._layout_terminals_grid(terminals)

        # id 映射
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

        # 顶点：只绘制端子
        for node in sorted(terminals, key=self._node_sort_key):
            cell_id = nid()
            id_map[node] = cell_id
            cab, blk, ter = node
            info = self.terminal_info_map.get(node)
            label_lines = f"{cab}/{blk}:{ter}"
            # label_lines 是字符串，之前错误地用 join；直接 escape
            label = escape(label_lines)
            x,y,w,h = positions.get(node, (40,40,120,48))
            style = "shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000"
            cells.append(f'<mxCell id="{cell_id}" value="{label}" style="{style}" vertex="1" parent="1">')
            cells.append(f'  <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>')
            cells.append('</mxCell>')

        # 构造要绘制的边集合：使用集合避免重复
        edges_to_draw = {}  # (a,b) tuple(sorted) -> label (如果多条来源，优先回路号)
        # 1) 先添加由 self.edges 中直接两端为端子的边（可能来自互联或回路节点连接）
        for e in self.edges:
            if len(e) != 2:
                continue
            a, b = tuple(e)
            if not (isinstance(a, tuple) and isinstance(b, tuple)):
                continue
            if a not in terminals or b not in terminals:
                continue
            key = tuple(sorted([a,b], key=self._node_sort_key))
            ai = self.terminal_info_map.get(a)
            bi = self.terminal_info_map.get(b)
            label = ""
            if ai and bi and ai.circuit_number and ai.circuit_number == bi.circuit_number:
                label = ai.circuit_number
            if key in edges_to_draw and edges_to_draw[key]:
                continue
            edges_to_draw[key] = label

        # 2) 对每个回路号，若包含多个端子，生成完全连通（每对标注回路号），并合并到 edges_to_draw
        circuits = defaultdict(list)
        for node in terminals:
            info = self.terminal_info_map.get(node)
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
                    key = tuple(sorted([a,b], key=self._node_sort_key))
                    # 回路号优先覆盖
                    edges_to_draw[key] = circ

        # 3) internal_wiring 作为全局名称：若多个端子引用相同 internal 名称，则在这些端子间生成完全连通
        internals = defaultdict(list)
        for node in terminals:
            info = self.terminal_info_map.get(node)
            if not info:
                continue
            for internal in info.internal_wiring:
                if internal:
                    internals[internal].append(node)

        for internal_name, nodes in internals.items():
            if len(nodes) < 2:
                continue
            nodes_sorted = sorted(nodes, key=self._node_sort_key)
            for i in range(len(nodes_sorted)):
                for j in range(i+1, len(nodes_sorted)):
                    a = nodes_sorted[i]
                    b = nodes_sorted[j]
                    key = tuple(sorted([a,b], key=self._node_sort_key))
                    # internal 标签仅在当前无回路标签的情况下写入，避免覆盖回路号
                    if key not in edges_to_draw or not edges_to_draw[key]:
                        edges_to_draw[key] = internal_name

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
    parser.add_argument("input_dir_path", type=str, help="包含端子排 Excel 文件的目录路径")
    parser.add_argument("--output_dir_path", type=str, default="outputs", help="输出 drawio 文件的目录路径")
    # parser.add_argument("--format", type=str, default="drawio", choices=["drawio", "svg"], help="输出文件格式，drawio 或 svg")
    args = parser.parse_args()
    
    xlsx_dir_path = args.input_dir_path
    
    terminal_blocks = []
    xlsx_path = Path(xlsx_dir_path)

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

# import pprint
    import pprint
    # 根据回路查询组件
    # comp = graph.get_component_by_circuit("A4061")
    # pprint.pprint(graph.summarize_component(comp))
    # graph.export_drawio_xml(comp, Path("circuit_A4061.drawio"), title="Circuit A4061")
    
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

