# -*- coding: utf-8 -*-
"""
生成 draw.io XML（不依赖 ports.csv，修正版）
- 正交连线：edgeStyle=orthogonalEdgeStyle，并在 style 中设置 exitX/exitY 与 entryX/entryY
- mark 元件不可连接（connectable=0）
- 自定义属性：写入到 <object ...> 上（而不是 mxCell 内）
- 端口定位：point(中心1)、line(1/2 两端，按较长边决定朝向)、face(1~8 从左上顺时针)，mark 无端口
- line 几何：按较长边为长度，较短边为固定“厚度”
- 元素 ID：组件=component_id（位于 <object> 或 mxCell），连线=wire_id
读取：./test_drawio/components.csv, wires.csv
输出：./test_drawio/schematic.drawio.xml
"""
import csv
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path("./manual_drawio")
COMP_FILE = BASE / "components.csv"
WIRE_FILE = BASE / "wires.csv"
OUT_FILE  = BASE / "schematic.drawio.xml"

MIN_LINE_THICKNESS = 10  # line 的最小厚度

# ---------------- 读取 CSV ----------------
components = {}
with open(COMP_FILE, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        components[row['component_id']] = row

wires = []
with open(WIRE_FILE, newline='', encoding='utf-8') as f:
    wires = list(csv.DictReader(f))

# ---------------- 工具函数 ----------------
def parse_properties(s: str):
    props = {}
    if not s:
        return props
    for part in s.split(';'):
        part = part.strip()
        if not part:
            continue
        if '=' in part:
            k, v = part.split('=', 1)
            props[k.strip()] = v.strip().strip('"')
        else:
            props[part] = ""
    return props

# 计算 line 最终几何尺寸（长度、厚度）
def normalize_line_wh(w: float, h: float):
    # 竖条：height >= width -> 宽=厚度，高=长度
    if h >= w:
        length = h if h > 0 else 60.0
        thickness = w if w > 0 else MIN_LINE_THICKNESS
        thickness = max(thickness, MIN_LINE_THICKNESS)
        return thickness, length  # (w, h)
    # 横条
    length = w if w > 0 else 80.0
    thickness = h if h > 0 else MIN_LINE_THICKNESS
    thickness = max(thickness, MIN_LINE_THICKNESS)
    return length, thickness

# 端口归一化坐标（0..1）
FACE_PORTS = {
    1:(0.0,0.0), 2:(0.5,0.0), 3:(1.0,0.0), 4:(1.0,0.5),
    5:(1.0,1.0), 6:(0.5,1.0), 7:(0.0,1.0), 8:(0.0,0.5)
}

def clamp_port(shape: str, idx: int):
    if shape == 'point':
        return 1
    if shape == 'line':
        return 1 if idx <= 1 else 2
    if shape == 'face':
        return min(8, max(1, idx))
    return None

# 返回端口的归一化位置（相对于最终几何宽高）
def port_frac(shape: str, w: float, h: float, idx: int):
    idx = clamp_port(shape, idx)
    if shape == 'point':
        return 0.5, 0.5
    if shape == 'line':
        # 此时 w,h 已是 normalize 之后的几何
        if h >= w:  # 竖条
            return (0.5, 0.0) if idx == 1 else (0.5, 1.0)
        else:       # 横条
            return (0.0, 0.5) if idx == 1 else (1.0, 0.5)
    if shape == 'face':
        return FACE_PORTS[idx]
    return None

# ---------------- 创建 XML ----------------
mxfile = ET.Element('mxfile', {"host":"app.diagrams.net"})
diagram = ET.SubElement(mxfile, 'diagram', {"name":"Page-1"})
model = ET.SubElement(diagram, 'mxGraphModel')
root = ET.SubElement(model, 'root')
ET.SubElement(root, 'mxCell', {"id":"0"})
ET.SubElement(root, 'mxCell', {"id":"1", "parent":"0"})

# 记录每个元件最终几何尺寸（用于连线锚点）
final_geom = {}

# ---------- 元件（vertex） ----------
for cid, comp in components.items():
    shape = (comp.get('shape') or '').strip()
    name  = comp.get('name') or cid
    x = float(comp.get('x') or 0)
    y = float(comp.get('y') or 0)
    w = float(comp.get('width') or 0)
    h = float(comp.get('height') or 0)
    group_id = comp.get('group_id', '')
    image_id = comp.get('image_id', '')
    props = parse_properties(comp.get('properties', ''))

    # 样式与几何
    if shape == 'point':
        if w <= 0: w = 16.0
        if h <= 0: h = 16.0
        style = 'shape=ellipse;perimeter=ellipsePerimeter;whiteSpace=wrap;html=1;aspect=fixed;'
        value_for_cell = name
        gw, gh = w, h
    elif shape == 'line':
        gw, gh = normalize_line_wh(w, h)
        style = 'shape=rectangle;whiteSpace=wrap;html=1;rounded=0;'
        value_for_cell = name
    elif shape == 'face':
        if w <= 0: w = 60.0
        if h <= 0: h = 40.0
        style = 'shape=rectangle;whiteSpace=wrap;html=1;rounded=0;'
        value_for_cell = name
        gw, gh = w, h
    elif shape == 'mark':
        text = props.get('text', name)
        font_size = props.get('font_size') or props.get('fontSize')
        if w <= 0: w = max(60.0, 8.0*len(text))
        if h <= 0: h = 24.0
        style = 'text;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;'
        if font_size:
            style += f'fontSize={font_size};'
        value_for_cell = text
        gw, gh = w, h
    else:
        # 未知按矩形
        if w <= 0: w = 60.0
        if h <= 0: h = 40.0
        style = 'shape=rectangle;whiteSpace=wrap;html=1;'
        value_for_cell = name
        gw, gh = w, h

    final_geom[cid] = (gw, gh)

    # 是否需要 <object> 包裹：当存在任意自定义属性 / group_id / image_id
    need_object = bool(props) or bool(group_id) or bool(image_id)

    if need_object:
        obj_attrs = {"id": cid, "label": value_for_cell}
        # 自定义属性添加到 object 上
        for k, v in props.items():
            obj_attrs[k] = str(v)
        if group_id:
            obj_attrs['group_id'] = group_id
        if image_id:
            obj_attrs['image_id'] = image_id
        obj = ET.SubElement(root, 'object', obj_attrs)
        mx_attrs = {"parent":"1", "vertex":"1", "style": style}
        if shape == 'mark':
            mx_attrs['connectable'] = '0'
        cell = ET.SubElement(obj, 'mxCell', mx_attrs)
    else:
        mx_attrs = {"id": cid, "value": value_for_cell, "parent":"1", "vertex":"1", "style": style}
        if shape == 'mark':
            mx_attrs['connectable'] = '0'
        cell = ET.SubElement(root, 'mxCell', mx_attrs)

    # geometry（注意 as 属性用字典传入）
    ET.SubElement(cell, 'mxGeometry', {"x":str(x), "y":str(y), "width":str(gw), "height":str(gh), "as":"geometry"})

# ---------- 连线（edge） ----------
for wrow in wires:
    wid = wrow.get('wire_id') or wrow.get('id') or wrow.get('name')
    from_id = wrow.get('from_component')
    to_id   = wrow.get('to_component')
    try:
        f_idx = int(wrow.get('from_port_index'))
        t_idx = int(wrow.get('to_port_index'))
    except Exception:
        continue

    from_comp = components.get(from_id)
    to_comp   = components.get(to_id)
    if not from_comp or not to_comp:
        continue
    if from_comp.get('shape') == 'mark' or to_comp.get('shape') == 'mark':
        # mark 不可连接
        continue

    # 取最终几何尺寸用于锚点归一化
    fw, fh = final_geom.get(from_id, (float(from_comp.get('width') or 0), float(from_comp.get('height') or 0)))
    tw, th = final_geom.get(to_id,   (float(to_comp.get('width') or 0),   float(to_comp.get('height') or 0)))

    # 归一化锚点
    ex, ey = port_frac(from_comp.get('shape'), fw, fh, f_idx)
    ix, iy = port_frac(to_comp.get('shape'),   tw, th, t_idx)
    if ex is None or ix is None:
        continue

    style = (
        'edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;rounded=0;html=1;endArrow=none;'
        f'exitX={ex};exitY={ey};exitPerimeter=1;entryX={ix};entryY={iy};entryPerimeter=1;'
    )

    edge_cell = ET.SubElement(root, 'mxCell', {
        'id': wid,
        'edge': '1',
        'parent': '1',
        'source': from_id,
        'target': to_id,
        'style': style
    })
    ET.SubElement(edge_cell, 'mxGeometry', {"relative":"1", "as":"geometry"})

# ---------------- 写文件 ----------------
ET.ElementTree(mxfile).write(OUT_FILE, encoding='utf-8', xml_declaration=True)
print("已生成:", OUT_FILE)
