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
 * 加载drawio文件的接口
 * @param {string} url - 文件的URL
 * @param {Object} other_args - 其他参数，支持 {readonly: boolean}
 * @returns {Promise<LocalFile>} 加载的文件对象
 */
function loadGraphXML(url, other_args = {}) {
    console.log(`loadGraphXML: Loading diagram from ${url}`, other_args);
    
    // 获取当前editorUi实例
    const editorUi = window.sb && window.sb.editorUi;
    if (!editorUi) {
        throw new Error('editorUi not available. Make sure the editor is loaded.');
    }
    
    // 检查当前文件状态
    const currentFile = editorUi.getCurrentFile();
    if (currentFile) {
        if (currentFile.isModified && currentFile.isModified()) {
            console.log('loadGraphXML: Current file is modified, continuing with load (modifications will be discarded)');
        } else {
            console.log('loadGraphXML: Discarding current unmodified file');
        }
    }
    
    // 使用DiagramLoader加载新文件
    const loader = new DiagramLoader(editorUi);
    const readonly = other_args.readonly || false;
    
    return loader.loadFromUrl(url, readonly);
}

/**
 * DiagramLoader：负责加载和设置diagram
 * 支持只读模式和切换为可编辑
 */
class DiagramLoader {
    /**
     * @param {App} editorUi
     */
    constructor(editorUi) {
        this.editorUi = editorUi || window.sb.editorUi;
        this._readonly = false;
    }

    /**
     * 从URL加载diagram
     * @param {string} url
     * @param {boolean} readonly 是否只读
     * @returns {Promise<LocalFile>}
     */
    loadFromUrl(url, readonly = false) {
        this._readonly = readonly;
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

                // 设置只读
                this.setReadonly(this._readonly);

                return file;
            });
    }

    /**
     * 设置只读或可编辑
     * @param {boolean} readonly
     */
    setReadonly(readonly = true) {
        this._readonly = readonly;
        if (this.editorUi && this.editorUi.editor && this.editorUi.editor.graph) {
            this.editorUi.editor.graph.setEnabled(!readonly);
        }
        // 可根据需要禁用/启用更多UI控件
    }

    /**
     * 开启编辑模式
     */
    enableEdit() {
        this.setReadonly(false);
    }

    /**
     * 开启只读模式
     */
    enableReadonly() {
        this.setReadonly(true);
    }

    /**
     * 当前是否只读
     */
    isReadonly() {
        return this._readonly;
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

    setHighlightColors(colors) {
        if (Array.isArray(colors) && colors.length > 0) {
            this._borderColors = colors;
            this._colorIndex = 0; // 重置颜色索引
            // 如果有高亮存在，更新颜色
            this.cellsWithHighlight.forEach(cell => {
                const hl = this.highlights.get(cell);
                if (hl) {
                    hl.setHighlightColor(this._getHighlightColor());
                    // 重新高亮以刷新颜色
                    hl.hide();
                    hl.highlight(this.graph.view.getState(cell));
                }
            });
        }
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

    // 等待 window.sb.editorUi 创建完毕
    function waitForEditorUi(callback, timeout = 10000) {
        const start = Date.now();
        (function check() {
            if (window.sb && window.sb.editorUi) {
                callback();
            } else if (Date.now() - start < timeout) {
                setTimeout(check, 200);
            } else {
                console.error("editorUi 加载超时");
            }
        })();
    }

    waitForEditorUi(() => {
        console.log("Plugin loaded: StripedOverlayManager");
        
        // 将loadGraphXML函数添加到全局window对象，方便调用
        window.loadGraphXML = loadGraphXML;

        setTimeout(() => {
            var url = "demo/manual.drawio.xml"; // 默认 URL
            if (url) {
                window.ohtoai.loader = new DiagramLoader(window.sb.editorUi);
                window.ohtoai.loader.loadFromUrl(url, true).then(() => {
                    console.log("Diagram loaded, initializing StripedOverlayManager");
                    const graph = window.sb.editorUi.editor.graph;
                    window.ohtoai.stripedOverlayManager = new StripedOverlayManager(graph);
                    window.ohtoai.stripedOverlayManager.startAutoHighlight(cell => {
                        if (!cell || !cell.value) return false;
                        if (typeof cell.value === "string") return false;
                        return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                    });
                    // 如需手动停止高亮，可调用 manager.clearHighlight() 或 manager.stopAutoHighlight()
                });
            }
        }, 1000);
    }, 120000);
});
