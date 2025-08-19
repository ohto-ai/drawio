import xml.etree.ElementTree as ET
from pathlib import Path

def extract_vertices_and_edges(file_path):
    """
    提取 vertex cell（图元）和 edge cell（连线），支持 object 内嵌 mxCell
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    vertices = {}
    edges = []

    for elem in root.iter():
        # object 内的 mxCell
        if elem.tag == 'object':
            obj_id = elem.get('id')
            value = elem.get('label', '') or elem.get('text', '') or ''
            attrs = {k: v for k, v in elem.attrib.items() if k not in ('id', 'label', 'text')}
            # 查找内部的 mxCell
            mxcell = elem.find('mxCell')
            if mxcell is not None and mxcell.get('vertex') == '1':
                vertices[obj_id] = {'id': obj_id, 'value': value, 'attrs': attrs}

        # 独立的 mxCell
        if elem.tag == 'mxCell':
            cid = elem.get('id')
            if not cid or cid in ('0', '1'):
                continue

            # edge
            if elem.get('edge') == '1':
                source = elem.get('source')
                target = elem.get('target')
                if source and target:
                    edges.append({'id': cid, 'source': source, 'target': target})
            # standalone vertex (不在 object 中)
            elif elem.get('vertex') == '1' and cid not in vertices:
                value = elem.get('value', '')
                vertices[cid] = {'id': cid, 'value': value, 'attrs': dict(elem.attrib)}

    return vertices, edges

def merge_diagrams(paths):
    merged_vertices = {}
    merged_edges = []

    for p in paths:
        vertices, edges = extract_vertices_and_edges(p)
        merged_vertices.update(vertices)
        merged_edges.extend(edges)

    return merged_vertices, merged_edges

if __name__ == "__main__":
    folder = Path("src/main/webapp/demo")
    files = list(folder.glob("*.drawio.xml"))

    vertices, edges = merge_diagrams(files)

    print("Vertices:")
    for cid, info in vertices.items():
        print(cid, info['value'], info['attrs'])

    print("\nEdges:")
    for e in edges:
        print(f"{e['source']} -> {e['target']} (edge {e['id']})")
