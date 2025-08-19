/**
 * file: js/mod.js
 * Description: This script loads a diagram from a URL specified in the query parameters.
 */

/**
 * 遍历对象树，查找含有指定属性或方法的对象
 * @param {object} root       - 搜索的根节点对象
 * @param {string} keyName    - 要查找的属性或方法名
 * @param {number} maxDepth   - 最大递归深度 (默认 3)
 * @returns {Array<{path: string, obj: object}>}
 */
function findObjectsWith(root, keyName, maxDepth = 3) {
  const seen = new WeakSet();
  const matches = [];

  function search(obj, path, depth) {
    if (obj == null || typeof obj !== "object") return;
    if (seen.has(obj)) return;
    seen.add(obj);

    try {
      if (keyName in obj) {
        if (typeof obj[keyName] === "function") {
          console.log("Found function:", path, obj);
        } else {
          console.log("Found property:", path, obj);
        }
        matches.push({ path, obj });
      }
    } catch (e) {
      // 某些对象属性访问可能报错，忽略
    }

    if (depth >= maxDepth) return;

    for (let key in obj) {
      try {
        const val = obj[key];
        if (val && typeof val === "object") {
          search(val, path + "." + key, depth + 1);
        }
      } catch (e) {
        // 有些 getter 会抛异常，忽略
      }
    }
  }

  search(root, "root", 0);
  return matches;
}

/**
 * DiagramLoader：负责加载和设置diagram
 */
class DiagramLoader {
    /**
     * @param {App} editorUi
     */
    constructor(editorUi) {
        this.editorUi = editorUi || window.sb.editorUi;
    }

    /**
     * 从URL加载diagram
     * @param {string} url
     * @returns {Promise<LocalFile>}
     */
    loadFromUrl(url) {
        return fetch(url)
            .then(resp => {
                const fileName = url.split('/').pop();
                const lastModified = resp.headers.get('Last-Modified');
                return resp.text().then(xml => ({
                    xml,
                    fileName,
                    url,
                    lastModified
                }));
            })
            .then(({ xml, fileName, url, lastModified }) => {
                const doc = mxUtils.parseXml(xml);
                var root = doc.documentElement;

                this.editorUi.editor.setGraphXml(root);
                this.editorUi.editor.setModified(false);

                var file = new LocalFile(this.editorUi, doc, fileName);
                this.editorUi.setCurrentFile(file);
                this.editorUi.updateDocumentTitle();
                this.editorUi.descriptorChanged();

                file.addListener(mxEvent.CHANGE, function(sender, evt){
                    console.log('文件内容改变了');
                });

                return file;
            });
    }
}

/**
 * StripedOverlayManager（高亮边框版）
 */
class StripedOverlayManager {
    constructor(graph, highlightStyle = {strokeColor: '#ff0000', imageBorder: 'light-dark(#ff0000, transparent)', strokeWidth: 4}) {
        this.graph = graph;
        this.highlightStyle = highlightStyle;
        this.cellsWithHighlight = new Set();
        this._originalStyles = new Map();

        // 蚂蚁线相关
        this._borderColors = ['#ff0000', '#ffff00']; // 红、黄
        this._colorIndex = 0;
        this._borderTimer = null;
        this._interval = 300; // ms
        this.mxConstants = window.mxConstants;
        this._autoHighlightTimer = null;
    }

    // 记录原始样式
    _saveOriginalStyle(cell) {
        if (!this._originalStyles.has(cell)) {
            const style = this.graph.getModel().getStyle(cell) || '';
            this._originalStyles.set(cell, style);
        }
    }

    // 应用高亮
    applyHighlight(cells) {
        cells.forEach(cell => {
            if (!this.cellsWithHighlight.has(cell)) {
                this._saveOriginalStyle(cell);
                this.cellsWithHighlight.add(cell);
            }
            this._setCellHighlightStyle(cell, this._borderColors[this._colorIndex]);
        });
        this._startBorderTimer();
    }

    // 设置单个cell的高亮样式
    _setCellHighlightStyle(cell, color) {
        let style = this._originalStyles.get(cell) || this.graph.getModel().getStyle(cell) || '';
        // 检查是否为图片图元
        const isImage = style.includes('shape=image') || style.includes('image=');
        // 合并高亮样式
        Object.entries(this.highlightStyle).forEach(([k, v]) => {
            style = style.replace(new RegExp(`${k}=[^;]*;?`, 'g'), '');
            if (k === 'strokeColor') {
                style += `${k}=${color};`;
            } else if (k === 'imageBorder') {
                style += `${k}=light-dark(${color}, transparent);`;
            } else {
                style += `${k}=${v};`;
            }
        });
        this.graph.getModel().setStyle(cell, style);
    }

    // 清除高亮
    clearHighlight() {
        if (this._borderTimer) {
            clearInterval(this._borderTimer);
            this._borderTimer = null;
        }
        if (this._autoHighlightTimer) {
            clearInterval(this._autoHighlightTimer);
            this._autoHighlightTimer = null;
        }
        this.cellsWithHighlight.forEach(cell => {
            if (this._originalStyles.has(cell)) {
                this.graph.getModel().setStyle(cell, this._originalStyles.get(cell));
            }
        });
        this.cellsWithHighlight.clear();
        this._originalStyles.clear();
    }

    // 更新高亮
    updateHighlight(callback) {
        const model = this.graph.getModel();
        model.filterDescendants(cell => {
            const shouldHighlight = callback(cell);
            const hasHighlight = this.cellsWithHighlight.has(cell);

            if (shouldHighlight && !hasHighlight) {
                this.applyHighlight([cell]);
            } else if (!shouldHighlight && hasHighlight) {
                if (this._originalStyles.has(cell)) {
                    this.graph.getModel().setStyle(cell, this._originalStyles.get(cell));
                }
                this.cellsWithHighlight.delete(cell);
                this._originalStyles.delete(cell);
            }
            return false;
        });
        if (this.cellsWithHighlight.size === 0 && this._borderTimer) {
            clearInterval(this._borderTimer);
            this._borderTimer = null;
        }
    }

    // 启动蚂蚁线定时器
    _startBorderTimer() {
        if (this._borderTimer) return;
        this._borderTimer = setInterval(() => {
            this._colorIndex = (this._colorIndex + 1) % this._borderColors.length;
            this.cellsWithHighlight.forEach(cell => {
                this._setCellHighlightStyle(cell, this._borderColors[this._colorIndex]);
            });
        }, this._interval);
    }

    /**
     * 自动高亮 alarm=1 的cell
     * @param {number} intervalMs
     */
    startAutoHighlightAlarm(intervalMs = 1000) {
        if (this._autoHighlightTimer) return;
        this._autoHighlightTimer = setInterval(() => {
            this.updateHighlight(
                cell => {
                    if (!cell || !cell.value) return false;
                    if (typeof cell.value === "string") return false;
                    return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                }
            );
        }, intervalMs);
    }
    stopAutoHighlightAlarm() {
        if (this._autoHighlightTimer) {
            clearInterval(this._autoHighlightTimer);
            this._autoHighlightTimer = null;
        }
    }
}

// 入口
window.addEventListener("load", () => {
    setTimeout(() => {
        console.log("Plugin loaded: StripedOverlayManager");

        setTimeout(() => {
            var url = "demo/manual.drawio.xml"; // 默认 URL
            if (url) {
                const loader = new DiagramLoader(window.sb.editorUi);
                loader.loadFromUrl(url).then(() => {
                    console.log("Diagram loaded, initializing StripedOverlayManager");
                    const graph = window.sb.editorUi.editor.graph;
                    const manager = new StripedOverlayManager(graph);
                    manager.startAutoHighlightAlarm(1000);
                    // 如需手动停止高亮，可调用 manager.clearHighlight() 或 manager.stopAutoHighlightAlarm()
                });
            }
        }, 1000);

    }, 1000); // 延时
});
