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
 * StripedOverlayManager（基于 mxCellHighlight，不修改 style）
 */
class StripedOverlayManager {
    constructor(graph, highlightColor = '#ff0000', strokeWidth = 4) {
        this.graph = graph;
        this.highlightColor = highlightColor;
        this.strokeWidth = strokeWidth;
        this.cellsWithHighlight = new Set();
        this.highlights = new Map();
        this._borderColors = ['#ff0000', '#ffff00'];
        this._colorIndex = 0;
        this._borderTimer = null;
        this._interval = 300;
        this._autoHighlightTimer = null;
    }

    // 应用高亮
    applyHighlight(cells) {
        cells.forEach(cell => {
            if (!this.cellsWithHighlight.has(cell)) {
                const hl = new mxCellHighlight(
                    this.graph,
                    this._getHighlightColor(),
                    this.strokeWidth
                );
                hl.highlight(this.graph.view.getState(cell));
                this.highlights.set(cell, hl);
                this.cellsWithHighlight.add(cell);
            }
        });
        this._startBorderTimer();
    }

    // 获取当前高亮色
    _getHighlightColor() {
        return this._borderColors[this._colorIndex];
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
        this.highlights.forEach(hl => hl.hide());
        this.highlights.clear();
        this.cellsWithHighlight.clear();
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
                const hl = this.highlights.get(cell);
                if (hl) hl.hide();
                this.highlights.delete(cell);
                this.cellsWithHighlight.delete(cell);
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
                const hl = this.highlights.get(cell);
                if (hl) {
                    hl.setHighlightColor(this._getHighlightColor());
                    // 重新高亮以刷新颜色
                    hl.hide();
                    hl.highlight(this.graph.view.getState(cell));
                }
            });
        }, this._interval);
    }

    /**
     * 自动高亮 alarm=1 的cell
     * @param {number} intervalMs
     */
    startAutoHighlight(callback, intervalMs = 1000) {
        if (this._autoHighlightTimer) return;
        this._autoHighlightTimer = setInterval(() => {
            this.updateHighlight(callback);
        }, intervalMs);
    }
    stopAutoHighlight() {
        if (this._autoHighlightTimer) {
            clearInterval(this._autoHighlightTimer);
            this._autoHighlightTimer = null;
        }
    }
}

// 入口
window.addEventListener("load", () => {
    window.ohtoai ||= {}
    setTimeout(() => {
        console.log("Plugin loaded: StripedOverlayManager");

        setTimeout(() => {
            var url = "demo/manual.drawio.xml"; // 默认 URL
            if (url) {
                window.ohtoai.loader = new DiagramLoader(window.sb.editorUi);
                window.ohtoai.loader.loadFromUrl(url).then(() => {
                    console.log("Diagram loaded, initializing StripedOverlayManager");
                    const graph = window.sb.editorUi.editor.graph;
                    window.ohtoai.manager = new StripedOverlayManager(graph);
                    window.ohtoai.manager.startAutoHighlight(cell => {
                        if (!cell || !cell.value) return false;
                        if (typeof cell.value === "string") return false;
                        return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                    });
                    // 如需手动停止高亮，可调用 manager.clearHighlight() 或 manager.stopAutoHighlight()
                });
            }
        }, 1000);

    }, 1000); // 延时
});
