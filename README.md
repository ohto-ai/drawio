# drawio

## 提取图元连接关系
```
$ python scripts/summary.py
Vertices:
C1 CMP1 {'alarm': '1', 'prop2': '3', 'group_id': 'G1', 'image_id': 'pic1'}
C2 CMP2 {'alarm': '2', 'prop2': '2', 'group_id': 'G2', 'image_id': 'pic2'}
C3 CMP3 {'alarm': '3', 'prop2': '3', 'group_id': 'G3', 'image_id': 'pic3'}
C4 Text4 {'font_size': '16'}
C5 Text5 {'font_size': '14'}
C6 CMP6 {'alarm': '1', 'prop2': '3', 'group_id': 'G3', 'image_id': 'pic6'}
C7 CMP7 {'alarm': '5', 'prop2': '1', 'group_id': 'G1', 'image_id': 'pic7'}
C8 CMP8 {'prop1': '3', 'prop2': '1', 'group_id': 'G2', 'image_id': 'pic8'}
C9 Text9 {'font_size': '14'}
C10 CMP10 {'prop1': '1', 'prop2': '5', 'group_id': 'G1', 'image_id': 'pic10'}

Edges:
C1 -> C2 (edge W1)
C2 -> C3 (edge W2)
C3 -> C6 (edge W3)
C6 -> C2 (edge W4)
C3 -> C8 (edge W5)
C6 -> C7 (edge W6)
C7 -> C10 (edge W7)
C10 -> C8 (edge W8)
```
