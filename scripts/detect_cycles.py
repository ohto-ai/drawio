#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网表环路检测脚本
通过汇总的components.csv和wires.csv表格，搜寻网表中存在的环路，
并将所有检测到的环路生成各自的draw.io XML文件，位置使用圆环分布。
"""

import csv
import math
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import sys
from collections import defaultdict, deque


def load_components(components_file):
    """Load components from summary_components.csv"""
    components = {}
    try:
        with open(components_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                components[row['component_id']] = {
                    'id': row['component_id'],
                    'shape': row['shape'],
                    'name': row['name'],
                    'group_id': row.get('group_id', ''),
                    'image_id': row.get('image_id', ''),
                    'properties': row.get('properties', ''),
                    'pages': row.get('pages', '').split(';') if row.get('pages') else []
                }
    except FileNotFoundError:
        print(f"Error: Components file '{components_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading components: {e}")
        sys.exit(1)
    
    return components


def load_wires(wires_file):
    """Load wires from summary_wires.csv"""
    wires = []
    try:
        with open(wires_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                wires.append({
                    'wire_id': row['wire_id'],
                    'from_component': row['from_component'],
                    'to_component': row['to_component'],
                    'page': row['page']
                })
    except FileNotFoundError:
        print(f"Error: Wires file '{wires_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading wires: {e}")
        sys.exit(1)
    
    return wires


def build_graph(wires):
    """Build adjacency list representation of the graph"""
    graph = defaultdict(set)
    all_components = set()
    
    for wire in wires:
        from_comp = wire['from_component']
        to_comp = wire['to_component']
        
        # Skip if either component is missing
        if not from_comp or not to_comp:
            continue
            
        graph[from_comp].add(to_comp)
        all_components.add(from_comp)
        all_components.add(to_comp)
    
    return graph, all_components


def find_cycles_dfs(graph):
    """Find all cycles in the graph using DFS"""
    WHITE = 0  # unvisited
    GRAY = 1   # currently being processed
    BLACK = 2  # completely processed
    
    colors = defaultdict(lambda: WHITE)
    cycles = []
    current_path = []
    
    def dfs(node):
        colors[node] = GRAY
        current_path.append(node)
        
        for neighbor in list(graph[node]):  # Create a list copy to avoid iteration issues
            if colors[neighbor] == GRAY:
                # Back edge found - cycle detected
                cycle_start_idx = current_path.index(neighbor)
                cycle = current_path[cycle_start_idx:] + [neighbor]
                cycles.append(cycle)
            elif colors[neighbor] == WHITE:
                dfs(neighbor)
        
        current_path.pop()
        colors[node] = BLACK
    
    # Start DFS from all unvisited nodes  
    all_nodes = list(graph.keys())  # Create a list copy to avoid iteration issues
    for node in all_nodes:
        if colors[node] == WHITE:
            dfs(node)
    
    return cycles


def remove_duplicate_cycles(cycles):
    """Remove duplicate cycles (same cycle but starting from different nodes)"""
    unique_cycles = []
    seen = set()
    
    for cycle in cycles:
        # Normalize cycle by finding the lexicographically smallest rotation
        if len(cycle) <= 1:
            continue
            
        # Remove the duplicate last node if it equals first
        clean_cycle = cycle[:-1] if len(cycle) > 1 and cycle[0] == cycle[-1] else cycle
        
        if len(clean_cycle) < 2:
            continue
        
        # Find all rotations
        rotations = []
        for i in range(len(clean_cycle)):
            rotation = tuple(clean_cycle[i:] + clean_cycle[:i])
            rotations.append(rotation)
        
        # Get the lexicographically smallest
        canonical = min(rotations)
        
        # Also check reverse direction
        reverse_cycle = list(reversed(clean_cycle))
        reverse_rotations = []
        for i in range(len(reverse_cycle)):
            rotation = tuple(reverse_cycle[i:] + reverse_cycle[:i])
            reverse_rotations.append(rotation)
        reverse_canonical = min(reverse_rotations)
        
        # Use the smaller of the two
        final_canonical = min(canonical, reverse_canonical)
        
        if final_canonical not in seen:
            seen.add(final_canonical)
            unique_cycles.append(list(final_canonical))
    
    return unique_cycles


def calculate_circular_positions(cycle_components, center_x=400, center_y=300, radius=200):
    """Calculate circular positions for components in a cycle"""
    positions = {}
    num_components = len(cycle_components)
    
    if num_components == 0:
        return positions
    
    for i, comp_id in enumerate(cycle_components):
        angle = (2 * math.pi * i) / num_components
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        
        positions[comp_id] = {
            'x': x,
            'y': y,
            'width': 100,
            'height': 60
        }
    
    return positions


def generate_cycle_xml(cycle, components, cycle_index, wires, output_dir):
    """Generate draw.io XML file for a single cycle with circular layout"""
    
    # Calculate positions
    positions = calculate_circular_positions(cycle)
    
    # Create XML structure
    root = ET.Element('mxfile', {
        'host': 'app.diagrams.net',
        'modified': '2023-01-01T00:00:00.000Z',
        'agent': 'cycle_detector',
        'version': '1.0'
    })
    
    diagram = ET.SubElement(root, 'diagram', {
        'id': f'cycle_{cycle_index}',
        'name': f'Cycle {cycle_index}'
    })
    
    # Create mxGraphModel
    graph_model = ET.SubElement(diagram, 'mxGraphModel', {
        'dx': '1422',
        'dy': '794',
        'grid': '1',
        'gridSize': '10',
        'guides': '1',
        'tooltips': '1',
        'connect': '1',
        'arrows': '1',
        'fold': '1',
        'page': '1',
        'pageScale': '1',
        'pageWidth': '827',
        'pageHeight': '1169',
        'math': '0',
        'shadow': '0'
    })
    
    root_elem = ET.SubElement(graph_model, 'root')
    ET.SubElement(root_elem, 'mxCell', {'id': '0'})
    ET.SubElement(root_elem, 'mxCell', {'id': '1', 'parent': '0'})
    
    # Add components
    component_id_counter = 2
    for comp_id in cycle:
        comp_info = components.get(comp_id, {})
        pos = positions[comp_id]
        
        # Determine style based on shape
        shape = comp_info.get('shape', 'face')
        if shape == 'point':
            style = 'ellipse;whiteSpace=wrap;html=1;'
        elif shape == 'line':
            style = 'rounded=0;whiteSpace=wrap;html=1;'
        elif shape == 'mark':
            style = 'text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;'
        else:  # face
            style = 'rounded=0;whiteSpace=wrap;html=1;'
        
        # Add component as mxCell
        cell = ET.SubElement(root_elem, 'mxCell', {
            'id': str(component_id_counter),
            'value': comp_info.get('name', comp_id),
            'style': style,
            'vertex': '1',
            'parent': '1'
        })
        
        # Add geometry
        geometry = ET.SubElement(cell, 'mxGeometry', {
            'x': str(pos['x']),
            'y': str(pos['y']),
            'width': str(pos['width']),
            'height': str(pos['height']),
            'as': 'geometry'
        })
        
        component_id_counter += 1
    
    # Add wires within the cycle
    component_to_xml_id = {comp_id: str(i + 2) for i, comp_id in enumerate(cycle)}
    
    for i in range(len(cycle)):
        from_comp = cycle[i]
        to_comp = cycle[(i + 1) % len(cycle)]
        
        # Find corresponding wire
        wire_id = None
        for wire in wires:
            if wire['from_component'] == from_comp and wire['to_component'] == to_comp:
                wire_id = wire['wire_id']
                break
        
        if wire_id:
            wire_cell = ET.SubElement(root_elem, 'mxCell', {
                'id': str(component_id_counter),
                'value': '',
                'style': 'endArrow=classic;html=1;rounded=0;',
                'edge': '1',
                'parent': '1',
                'source': component_to_xml_id[from_comp],
                'target': component_to_xml_id[to_comp]
            })
            
            ET.SubElement(wire_cell, 'mxGeometry', {
                'width': '50',
                'height': '50',
                'relative': '1',
                'as': 'geometry'
            })
            
            component_id_counter += 1
    
    # Write XML file
    filename = f'cycle_{cycle_index}.drawio.xml'
    output_path = output_dir / filename
    
    # Pretty print XML
    import xml.dom.minidom
    rough_string = ET.tostring(root, encoding='unicode')
    reparsed = xml.dom.minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent='  ')
    
    # Remove extra blank lines
    pretty_lines = [line for line in pretty_xml.split('\n') if line.strip()]
    final_xml = '\n'.join(pretty_lines)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_xml)
    
    print(f"Generated {filename} with {len(cycle)} components")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Detect cycles in netlist and generate draw.io XML files for each cycle',
        epilog='''
        This script reads summary_components.csv and summary_wires.csv files,
        detects all cycles in the component connection graph, and generates
        individual draw.io XML files for each cycle with circular layout.
        
        Usage example:
        1. First extract netlist: python3 extract_netlist.py src/main/webapp/demo -o netlist_out
        2. Then detect cycles: python3 detect_cycles.py netlist_out -o cycles_out
        
        The generated XML files can be opened in draw.io to visualize the detected cycles.
        '''
    )
    parser.add_argument('input_dir', nargs='?', default='netlist_output',
                       help='Directory containing summary CSV files (default: netlist_output)')
    parser.add_argument('-o', '--output', default='cycles_output',
                       help='Output directory for cycle XML files (default: cycles_output)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)
    
    components_file = input_dir / 'summary_components.csv'
    wires_file = input_dir / 'summary_wires.csv'
    
    if not components_file.exists():
        print(f"Error: Components file '{components_file}' does not exist")
        sys.exit(1)
        
    if not wires_file.exists():
        print(f"Error: Wires file '{wires_file}' does not exist")
        sys.exit(1)
    
    # Load data
    print("Loading components and wires...")
    components = load_components(components_file)
    wires = load_wires(wires_file)
    
    print(f"Loaded {len(components)} components and {len(wires)} wires")
    
    # Build graph
    graph, all_components = build_graph(wires)
    print(f"Built graph with {len(all_components)} nodes and {len(wires)} edges")
    
    if args.verbose:
        print("Graph adjacency list:")
        for node, neighbors in graph.items():
            print(f"  {node} -> {', '.join(neighbors)}")
    
    # Find cycles
    print("Detecting cycles...")
    cycles = find_cycles_dfs(graph)
    unique_cycles = remove_duplicate_cycles(cycles)
    
    print(f"Found {len(unique_cycles)} unique cycles")
    
    if not unique_cycles:
        print("No cycles detected in the netlist.")
        return
    
    # Create output directory
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Generate XML files for each cycle
    print(f"\nGenerating XML files in '{output_dir}':")
    for i, cycle in enumerate(unique_cycles, 1):
        if args.verbose:
            print(f"Cycle {i}: {' -> '.join(cycle + [cycle[0]])}")
        
        generate_cycle_xml(cycle, components, i, wires, output_dir)
    
    print(f"\nCycle detection completed! Generated {len(unique_cycles)} XML files.")
    print("Generated files:")
    for xml_file in sorted(output_dir.glob("cycle_*.drawio.xml")):
        print(f"  {xml_file.name}")


if __name__ == "__main__":
    main()