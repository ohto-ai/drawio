#!/usr/bin/env python3
"""
简单测试脚本：验证互联类型功能
"""

import sys
import os
import pandas as pd
import tempfile
import shutil

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from terminal_data_model import TerminalDataModel, COMPONENT_GRAPHICS

def test_connection_types():
    """测试互联类型功能"""
    
    print("=" * 60)
    print("测试互联类型功能")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建测试数据
        # 1. 后端装置互联数据（包含互联类型列）
        backend_connections_data = {
            "设备编号": ["1ABA03GG003", "1ABA03GG003", "1ABA03GG003"],
            "互联起点": ["61LHn", "1DK:1", "42LHa"],
            "互联终点": ["1DK:1", "61LHNa", "42LHb"],
            "互联类型": ["", "刀开关", ""]  # 第二行使用刀开关作为互联类型
        }
        
        # 2. 后端装置布局数据
        backend_devices_data = {
            "设备编号": ["1ABA03GG003", "1ABA03GG003"],
            "装置编号": ["61LH", "61LH"],
            "装置组编号": ["61LH", "61LH"],
            "布局端子": ["61LHn", "61LHNa"]
        }
        
        # 3. 后端元件数据
        backend_components_data = {
            "设备编号": ["1ABA03GG003", "1ABA03GG003"],
            "元件编号": ["1DK", "42LH"],
            "元件类型": ["刀开关", "LED"],
            "元件端子": ["1DK:1", "42LHa;42LHb"]
        }
        
        # 保存为Excel文件
        excel_file = os.path.join(temp_dir, "test_data.xlsx")
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            pd.DataFrame(backend_connections_data).to_excel(writer, sheet_name="互联数据", index=False)
            pd.DataFrame(backend_devices_data).to_excel(writer, sheet_name="装置布局", index=False)
            pd.DataFrame(backend_components_data).to_excel(writer, sheet_name="元件数据", index=False)
        
        print(f"\n创建测试数据文件: {excel_file}")
        
        # 加载数据
        model = TerminalDataModel()
        model.load_xlsxs([excel_file])
        
        print("\n数据加载完成")
        print(f"机柜数量: {len(model.cabinets)}")
        
        # 检查backend_connections
        for cabinet in model.cabinets:
            print(f"\n机柜: {cabinet.id}")
            print(f"  后端连接数: {len(cabinet.backend_connections)}")
            for i, bc in enumerate(cabinet.backend_connections):
                print(f"  连接 {i+1}: {bc.from_terminal} -> {bc.to_terminal}")
                print(f"    互联类型: {bc.connection_type if bc.connection_type else '(直接连线)'}")
        
        # 构建连接图
        print("\n构建连接图...")
        graph = model.build_connection_graph()
        
        print(f"节点数: {len(graph.nodes)}")
        print(f"边数: {len(graph.edges)}")
        print(f"带连接类型的边数: {len(graph.connection_types)}")
        
        # 检查连接类型
        for key, conn_type in graph.connection_types.items():
            a, b = graph.repr_map[key]
            print(f"  {a} <-> {b}: 连接类型={conn_type}")
        
        # 导出到drawio
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n导出到 {output_dir}...")
        out_paths = model.export_drawio_groups(output_dir)
        
        print(f"\n成功导出 {len(out_paths)} 个文件:")
        for path in out_paths:
            file_size = os.path.getsize(path)
            print(f"  {os.path.basename(path)} ({file_size} bytes)")
        
        # 验证生成的XML文件包含刀开关元素
        for path in out_paths:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "刀开关" in str(COMPONENT_GRAPHICS.get("刀开关", {}).get("style", "")):
                    # 检查是否包含刀开关的样式
                    if COMPONENT_GRAPHICS["刀开关"]["style"] in content:
                        print(f"\n✓ 文件 {os.path.basename(path)} 包含刀开关元素")
                    else:
                        print(f"\n✗ 文件 {os.path.basename(path)} 未找到刀开关元素")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n清理临时目录: {temp_dir}")

if __name__ == "__main__":
    success = test_connection_types()
    sys.exit(0 if success else 1)
