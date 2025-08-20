import xml.etree.ElementTree as ET
from pathlib import Path
import csv
import math

def classify_shape(style, width, height, value):
    """
    Classify component shape based on style, dimensions and content
    """
    if not style:
        style = ""
    
    # Text elements are typically marks
    if "text;" in style or "fontSize" in style:
        return "mark"
    
    # Points are typically small circular elements
    if "ellipse" in style or "circle" in style:
        return "point"
    
    # Lines are thin rectangular elements  
    if width > 0 and height > 0:
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 5:  # Very elongated shape
            return "line"
    
    # Face elements are larger rectangular components
    if "rectangle" in style and width > 50 and height > 50:
        return "face"
    
    # Default to point for small elements, line for medium, face for large
    if width <= 20 and height <= 20:
        return "point"
    elif width <= 20 or height <= 20:
        return "line"
    else:
        return "face"

def get_port_index_from_coordinates(exit_x, exit_y, entry_x, entry_y, is_source):
    """
    Map exit/entry coordinates to port indices
    Coordinates are typically 0.0-1.0 representing position on perimeter
    """
    if is_source:
        x, y = exit_x, exit_y
    else:
        x, y = entry_x, entry_y
        
    if x is None or y is None:
        return 1  # Default port
    
    try:
        x, y = float(x), float(y)
    except:
        return 1
        
    # Map coordinates to 8 ports around perimeter
    # Top: y=0, ports 1-3
    # Right: x=1, ports 3-5 
    # Bottom: y=1, ports 5-7
    # Left: x=0, ports 7-1
    
    if abs(y) < 0.1:  # Top edge
        if x < 0.33:
            return 1
        elif x < 0.67:
            return 2
        else:
            return 3
    elif abs(x - 1.0) < 0.1:  # Right edge
        if y < 0.33:
            return 3
        elif y < 0.67:
            return 4
        else:
            return 5
    elif abs(y - 1.0) < 0.1:  # Bottom edge
        if x > 0.67:
            return 5
        elif x > 0.33:
            return 6
        else:
            return 7
    elif abs(x) < 0.1:  # Left edge
        if y > 0.67:
            return 7
        elif y > 0.33:
            return 8
        else:
            return 1
    else:
        # Interior point, default to center port
        return 1

def format_properties(attrs):
    """
    Format component attributes as properties string
    """
    if not attrs:
        return ""
    
    # Filter out standard attributes that aren't properties
    skip_attrs = {'id', 'label', 'text', 'group_id', 'image_id'}
    
    prop_parts = []
    for k, v in attrs.items():
        if k not in skip_attrs:
            if ' ' in str(v) or '"' in str(v):
                prop_parts.append(f'{k}="{v}"')
            else:
                prop_parts.append(f'{k}={v}')
    
    return ";".join(prop_parts)

def extract_vertices_and_edges(file_path):
    """
    提取 vertex cell（图元）和 edge cell（连线），支持 object 内嵌 mxCell
    同时提取几何信息和页面信息
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Handle multi-page documents
    pages_data = []
    
    # Find all diagram elements
    diagrams = root.findall('.//diagram')
    if not diagrams:
        # Single page document, treat root as single page
        diagrams = [root]
    
    for diagram_idx, diagram in enumerate(diagrams):
        page_name = diagram.get('name', f'Page-{diagram_idx + 1}')
        vertices = {}
        edges = []
        
        # Find the graph model
        if diagram.tag == 'diagram':
            # Multi-page format
            graph_model = diagram.find('.//mxGraphModel')
            if graph_model is None:
                continue
            root_elem = graph_model.find('root')
        else:
            # Single page format
            root_elem = diagram
            
        if root_elem is None:
            continue

        for elem in root_elem.iter():
            # object 内的 mxCell
            if elem.tag == 'object':
                obj_id = elem.get('id')
                if not obj_id or obj_id in ('0', '1'):
                    continue
                    
                value = elem.get('label', '') or elem.get('text', '') or ''
                attrs = {k: v for k, v in elem.attrib.items() if k not in ('id', 'label', 'text')}
                
                # 查找内部的 mxCell
                mxcell = elem.find('mxCell')
                if mxcell is not None and mxcell.get('vertex') == '1':
                    # Extract geometry information
                    geometry = mxcell.find('mxGeometry')
                    x, y, width, height = 0, 0, 0, 0
                    style = mxcell.get('style', '')
                    
                    if geometry is not None:
                        x = float(geometry.get('x', 0))
                        y = float(geometry.get('y', 0))  
                        width = float(geometry.get('width', 0))
                        height = float(geometry.get('height', 0))
                    
                    # Classify shape
                    shape = classify_shape(style, width, height, value)
                    
                    vertices[obj_id] = {
                        'id': obj_id, 
                        'value': value, 
                        'attrs': attrs,
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height,
                        'style': style,
                        'shape': shape
                    }

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
                        # Extract connection point information from style attribute
                        style = elem.get('style', '')
                        exit_x = exit_y = entry_x = entry_y = None
                        
                        # Parse style string for coordinates
                        for part in style.split(';'):
                            if '=' in part:
                                key, value = part.split('=', 1)
                                if key == 'exitX':
                                    exit_x = value
                                elif key == 'exitY':
                                    exit_y = value
                                elif key == 'entryX':
                                    entry_x = value
                                elif key == 'entryY':
                                    entry_y = value
                        
                        from_port = get_port_index_from_coordinates(exit_x, exit_y, entry_x, entry_y, True)
                        to_port = get_port_index_from_coordinates(exit_x, exit_y, entry_x, entry_y, False)
                        
                        edges.append({
                            'id': cid, 
                            'source': source, 
                            'target': target,
                            'from_port': from_port,
                            'to_port': to_port,
                            'exit_x': exit_x,
                            'exit_y': exit_y,
                            'entry_x': entry_x,
                            'entry_y': entry_y
                        })
                        
                # standalone vertex (不在 object 中)
                elif elem.get('vertex') == '1' and cid not in vertices:
                    value = elem.get('value', '')
                    attrs = dict(elem.attrib)
                    
                    # Extract geometry information
                    geometry = elem.find('mxGeometry')
                    x, y, width, height = 0, 0, 0, 0
                    style = elem.get('style', '')
                    
                    if geometry is not None:
                        x = float(geometry.get('x', 0))
                        y = float(geometry.get('y', 0))
                        width = float(geometry.get('width', 0))
                        height = float(geometry.get('height', 0))
                    
                    shape = classify_shape(style, width, height, value)
                    
                    vertices[cid] = {
                        'id': cid, 
                        'value': value, 
                        'attrs': attrs,
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height,
                        'style': style,
                        'shape': shape
                    }

        pages_data.append({
            'name': page_name,
            'vertices': vertices,
            'edges': edges
        })
    
    return pages_data

def generate_page_csvs(page_data, output_dir):
    """
    Generate components.csv and wires.csv for a single page
    """
    page_dir = output_dir / page_data['name']
    page_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate components.csv
    components_file = page_dir / 'components.csv'
    with open(components_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['component_id', 'shape', 'name', 'x', 'y', 'width', 'height', 'group_id', 'image_id', 'properties'])
        
        for comp_id, comp_data in page_data['vertices'].items():
            attrs = comp_data['attrs']
            group_id = attrs.get('group_id', '')
            image_id = attrs.get('image_id', '')
            properties = format_properties(attrs)
            
            writer.writerow([
                comp_id,
                comp_data['shape'],
                comp_data['value'],
                comp_data['x'],
                comp_data['y'],
                comp_data['width'],
                comp_data['height'],
                group_id,
                image_id,
                properties
            ])
    
    # Generate wires.csv
    wires_file = page_dir / 'wires.csv'
    with open(wires_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['wire_id', 'from_component', 'from_port_index', 'to_component', 'to_port_index', 'path'])
        
        for edge in page_data['edges']:
            writer.writerow([
                edge['id'],
                edge['source'],
                edge['from_port'],
                edge['target'],
                edge['to_port'],
                ''  # path - empty for now
            ])

def generate_summary_csvs(all_pages_data, output_dir):
    """
    Generate summary CSV files consolidating all pages
    """
    # Collect all components across pages
    all_components = {}
    all_wires = []
    
    for page_data in all_pages_data:
        page_name = page_data['name']
        
        # Collect components (same ID considered same component)
        for comp_id, comp_data in page_data['vertices'].items():
            if comp_id not in all_components:
                attrs = comp_data['attrs']
                all_components[comp_id] = {
                    'id': comp_id,
                    'shape': comp_data['shape'],
                    'name': comp_data['value'],
                    'group_id': attrs.get('group_id', ''),
                    'image_id': attrs.get('image_id', ''),
                    'properties': format_properties(attrs),
                    'pages': [page_name]
                }
            else:
                # Add page to existing component
                if page_name not in all_components[comp_id]['pages']:
                    all_components[comp_id]['pages'].append(page_name)
        
        # Collect all wires
        for edge in page_data['edges']:
            all_wires.append({
                'wire_id': edge['id'],
                'from_component': edge['source'],
                'from_port_index': edge['from_port'],
                'to_component': edge['target'],
                'to_port_index': edge['to_port'],
                'path': '',
                'page': page_name
            })
    
    # Write summary components.csv (without x,y coordinates)
    summary_components_file = output_dir / 'summary_components.csv'
    with open(summary_components_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['component_id', 'shape', 'name', 'group_id', 'image_id', 'properties', 'pages'])
        
        for comp_id, comp_data in all_components.items():
            writer.writerow([
                comp_id,
                comp_data['shape'],
                comp_data['name'],
                comp_data['group_id'],
                comp_data['image_id'],
                comp_data['properties'],
                ';'.join(comp_data['pages'])
            ])
    
    # Write summary wires.csv
    summary_wires_file = output_dir / 'summary_wires.csv'
    with open(summary_wires_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['wire_id', 'from_component', 'from_port_index', 'to_component', 'to_port_index', 'path', 'page'])
        
        for wire in all_wires:
            writer.writerow([
                wire['wire_id'],
                wire['from_component'],
                wire['from_port_index'],
                wire['to_component'],
                wire['to_port_index'],
                wire['path'],
                wire['page']
            ])

def merge_diagrams(paths):
    """
    Process multiple drawio files and extract all page data
    """
    all_pages_data = []
    
    for file_path in paths:
        pages_data = extract_vertices_and_edges(file_path)
        
        # Add file info to page names to avoid conflicts
        file_name = Path(file_path).stem
        for page_data in pages_data:
            if len(pages_data) > 1:
                # Multi-page file, keep original page names but prefix with filename
                page_data['name'] = f"{file_name}_{page_data['name']}"
            else:
                # Single page file, use filename as page name
                page_data['name'] = file_name
                
        all_pages_data.extend(pages_data)
    
    return all_pages_data

if __name__ == "__main__":
    folder = Path("src/main/webapp/demo")
    files = list(folder.glob("*.drawio.xml"))
    
    if not files:
        print("No drawio.xml files found in the demo folder")
        exit(1)

    # Extract data from all files
    all_pages_data = merge_diagrams(files)
    
    # Create output directory
    output_dir = Path("netlist_output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Processing {len(files)} file(s) with {len(all_pages_data)} page(s)")
    
    # Generate CSV files for each page
    for page_data in all_pages_data:
        print(f"Generating CSV files for page: {page_data['name']}")
        generate_page_csvs(page_data, output_dir)
        
        # Print summary for verification
        print(f"  Components: {len(page_data['vertices'])}")
        print(f"  Wires: {len(page_data['edges'])}")
    
    # Generate summary CSV files
    print("Generating summary CSV files...")
    generate_summary_csvs(all_pages_data, output_dir)
    
    print(f"\nNetlist export completed! Output saved to: {output_dir}")
    print("Files generated:")
    for file_path in sorted(output_dir.rglob("*.csv")):
        print(f"  {file_path}")
        
    # Also print old format for comparison
    print("\n" + "="*50)
    print("Legacy format output (for comparison):")
    print("="*50)
    
    for page_data in all_pages_data:
        print(f"\nPage: {page_data['name']}")
        print("Vertices:")
        for cid, info in page_data['vertices'].items():
            print(f"  {cid}: {info['value']} (shape={info['shape']}, pos=({info['x']},{info['y']}), size=({info['width']}x{info['height']}))")

        print("Edges:")
        for e in page_data['edges']:
            print(f"  {e['source']} -> {e['target']} (edge {e['id']}, ports {e['from_port']}->{e['to_port']})")
