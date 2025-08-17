# -*- coding: utf-8 -*-
"""
完整脚本：随机生成三张测试 CSV 文件
1) components.csv
2) ports.csv
3) wires.csv
生成的数据包含合理的尺寸、位置和连接关系
"""
import csv
import random
from pathlib import Path

BASE = Path("./test_drawio")
BASE.mkdir(parents=True, exist_ok=True)

num_components = 10  # 随机生成组件数量
shapes = ["point", "line", "face", "mark"]
components = [["component_id","shape","name","x","y","width","height","group_id","image_id","properties"]]
ports = [["port_index","component_id","name"]]
wires = [["wire_id","from_component","from_port_index","to_component","to_port_index","path"]]

for i in range(1, num_components+1):
    cid = f"C{i}"
    shape = random.choice(shapes)
    name = f"CMP{i}"
    x = random.randint(50, 500)
    y = random.randint(50, 400)
    if shape == "point":
        w = h = random.randint(10,20)
    elif shape == "line":
        w = random.randint(40,100)
        h = random.randint(0,10)
    elif shape == "face":
        w = random.randint(20,80)
        h = random.randint(20,60)
    else:  # mark
        w = h = 0
    group_id = f"G{random.randint(1,3)}" if shape != "mark" else ""
    image_id = f"pic{i}" if shape != "mark" else ""
    if shape == "mark":
        props = f'text="Text{i}";font_size={random.choice([12,14,16,18])}'
    else:
        props = f"prop1={random.randint(1,5)};prop2={random.randint(1,5)}"
    components.append([cid, shape, name, x, y, w, h, group_id, image_id, props])

    # 生成端口
    if shape == "point":
        ports.append([1, cid, f"P1"])
    elif shape == "line":
        ports.append([1, cid, f"P1"])
        ports.append([2, cid, f"P2"])
    elif shape == "face":
        for idx in range(1,9):
            ports.append([idx, cid, f"P{idx}"])
    # mark 没有端口

# 随机生成 wires，每个 wire 连接两个不同组件
wire_id_counter = 1
all_ports = [f"{p[1]}.{p[0]}" for p in ports[1:]]
for _ in range(num_components*2):
    from_port = random.choice(all_ports)
    to_port = random.choice([p for p in all_ports if p.split('.')[0] != from_port.split('.')[0]])
    wires.append([f"W{wire_id_counter}", from_port.split('.')[0], int(from_port.split('.')[1]),
                  to_port.split('.')[0], int(to_port.split('.')[1]), ""])
    wire_id_counter += 1

# 写入 CSV 文件
for filename, data in [("components.csv", components),
                       ("ports.csv", ports),
                       ("wires.csv", wires)]:
    filepath = BASE / filename
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)
    print(f"{filename} 写入完成：{filepath}")

print("所有随机测试 CSV 文件生成完毕")
