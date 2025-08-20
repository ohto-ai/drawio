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
 * @param {boolean} readonly - 是否只读模式，默认为false
 * @returns {Promise<LocalFile>} 加载的文件对象
 */
function loadGraphXML(url, readonly = false) {
    console.log(`loadGraphXML: Loading diagram from ${url}`, { readonly });
    
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
    
    // 从URL获取XML数据并使用editorUi的fileLoaded方法来正确加载文件
    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch file: ${response.status} ${response.statusText}`);
            }
            return response.text();
        })
        .then(xmlData => {
            // 获取文件名
            const fileName = url.split('/').pop() || 'diagram.drawio.xml';
            
            // 创建LocalFile实例 - 这是DrawIO正确的文件加载方式
            const localFile = new LocalFile(editorUi, xmlData, fileName, true);
            
            // 如果需要只读模式，设置文件为不可编辑
            if (readonly) {
                localFile.setEditable(false);
            }
            
            // 使用editorUi的fileLoaded方法来正确加载文件
            // 这会处理所有必要的状态更新、UI刷新等
            editorUi.fileLoaded(localFile);
            
            // 如果是只读模式，禁用图形编辑
            if (readonly && editorUi.editor && editorUi.editor.graph) {
                editorUi.editor.graph.setEnabled(false);
            }
            
            console.log('loadGraphXML: File loaded successfully', { fileName, readonly });
            return localFile;
        })
        .catch(error => {
            console.error('loadGraphXML: Error loading file', error);
            throw error;
        });
}

/**
 * 启用编辑功能
 * @returns {boolean} 成功返回true，失败返回false
 */
function enableEditing() {
    console.log('enableEditing: Enabling editor');
    
    try {
        const editorUi = window.sb && window.sb.editorUi;
        if (!editorUi) {
            console.error('enableEditing: editorUi not available');
            return false;
        }
        
        // 启用图形编辑
        if (editorUi.editor && editorUi.editor.graph) {
            editorUi.editor.graph.setEnabled(true);
            console.log('enableEditing: Graph editing enabled');
        }
        
        // 设置当前文件为可编辑
        const currentFile = editorUi.getCurrentFile();
        if (currentFile && typeof currentFile.setEditable === 'function') {
            currentFile.setEditable(true);
            console.log('enableEditing: File set as editable');
        }
        
        console.log('enableEditing: Editing enabled successfully');
        return true;
    } catch (error) {
        console.error('enableEditing: Error enabling editing', error);
        return false;
    }
}

/**
 * 禁用编辑功能（只读模式）
 * @returns {boolean} 成功返回true，失败返回false
 */
function disableEditing() {
    console.log('disableEditing: Disabling editor');
    
    try {
        const editorUi = window.sb && window.sb.editorUi;
        if (!editorUi) {
            console.error('disableEditing: editorUi not available');
            return false;
        }
        
        // 禁用图形编辑
        if (editorUi.editor && editorUi.editor.graph) {
            editorUi.editor.graph.setEnabled(false);
            console.log('disableEditing: Graph editing disabled');
        }
        
        // 设置当前文件为不可编辑
        const currentFile = editorUi.getCurrentFile();
        if (currentFile && typeof currentFile.setEditable === 'function') {
            currentFile.setEditable(false);
            console.log('disableEditing: File set as non-editable');
        }
        
        console.log('disableEditing: Editing disabled successfully');
        return true;
    } catch (error) {
        console.error('disableEditing: Error disabling editing', error);
        return false;
    }
}

/**
 * 检查当前是否启用编辑
 * @returns {boolean} 如果启用编辑返回true，否则返回false
 */
function isEditingEnabled() {
    try {
        const editorUi = window.sb && window.sb.editorUi;
        if (!editorUi) {
            return false;
        }
        
        // 检查图形是否启用
        const graphEnabled = editorUi.editor && editorUi.editor.graph ? 
            editorUi.editor.graph.isEnabled() : false;
        
        // 检查文件是否可编辑
        const currentFile = editorUi.getCurrentFile();
        const fileEditable = currentFile && typeof currentFile.isEditable === 'function' ? 
            currentFile.isEditable() : true;
        
        return graphEnabled && fileEditable;
    } catch (error) {
        console.error('isEditingEnabled: Error checking editing status', error);
        return false;
    }
}



/**
 * StripedOverlayManager（基于 mxCellHighlight，不修改 style）
 * 支持两类高亮：条件高亮和指定高亮，具有优先级系统
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
        
        // 新增：多个条件高亮支持
        this._conditionalHighlights = [];  // [{id, callback, colors, colorIndex}]
        
        // 新增：多个指定高亮支持  
        this._specificHighlights = [];     // [{id, cells, colors, colorIndex}]
        
        // 新增：追踪每个cell的高亮信息 {cell -> {type, id, highlight}}
        this._cellHighlightInfo = new Map();
    }

    /**
     * 添加条件高亮
     * @param {string} id - 高亮标识符
     * @param {function} callback - 判断函数
     * @param {string[]} colors - 颜色组数组
     * @returns {boolean} 是否添加成功
     */
    addConditionalHighlight(id, callback, colors) {
        if (!id || typeof callback !== 'function' || !Array.isArray(colors) || colors.length === 0) {
            return false;
        }
        
        // 移除已存在的同id高亮
        this.removeConditionalHighlight(id);
        
        this._conditionalHighlights.push({
            id: id,
            callback: callback,
            colors: colors,
            colorIndex: 0
        });
        
        return true;
    }

    /**
     * 移除条件高亮
     * @param {string} id - 高亮标识符
     * @returns {boolean} 是否移除成功
     */
    removeConditionalHighlight(id) {
        const index = this._conditionalHighlights.findIndex(h => h.id === id);
        if (index >= 0) {
            this._conditionalHighlights.splice(index, 1);
            this._refreshHighlights();
            return true;
        }
        return false;
    }

    /**
     * 添加指定高亮
     * @param {string} id - 高亮标识符
     * @param {object[]} cells - 要高亮的cell数组
     * @param {string[]} colors - 颜色组数组
     * @returns {boolean} 是否添加成功
     */
    addSpecificHighlight(id, cells, colors) {
        if (!id || !Array.isArray(cells) || !Array.isArray(colors) || colors.length === 0) {
            return false;
        }
        
        // 移除已存在的同id高亮
        this.removeSpecificHighlight(id);
        
        this._specificHighlights.push({
            id: id,
            cells: new Set(cells),
            colors: colors,
            colorIndex: 0
        });
        
        return true;
    }

    /**
     * 移除指定高亮
     * @param {string} id - 高亮标识符
     * @returns {boolean} 是否移除成功
     */
    removeSpecificHighlight(id) {
        const index = this._specificHighlights.findIndex(h => h.id === id);
        if (index >= 0) {
            this._specificHighlights.splice(index, 1);
            this._refreshHighlights();
            return true;
        }
        return false;
    }

    /**
     * 刷新所有高亮 - 重新计算并应用高亮
     */
    _refreshHighlights() {
        // 清除所有现有高亮
        this._clearAllHighlights();
        
        // 获取所有需要高亮的cells
        const model = this.graph.getModel();
        const cellsToHighlight = new Map(); // cell -> {type, id, colors, colorIndex}
        
        // 遍历所有cells并应用高亮逻辑
        model.filterDescendants(cell => {
            let highlightInfo = null;
            
            // 1. 检查条件高亮 (从后往前，最后的优先)
            for (let i = this._conditionalHighlights.length - 1; i >= 0; i--) {
                const condHighlight = this._conditionalHighlights[i];
                try {
                    if (condHighlight.callback(cell)) {
                        highlightInfo = {
                            type: 'conditional',
                            id: condHighlight.id,
                            colors: condHighlight.colors,
                            colorIndex: condHighlight.colorIndex
                        };
                        break; // 短路测试，第一个匹配的就使用
                    }
                } catch (e) {
                    console.warn(`条件高亮回调函数出错 (id: ${condHighlight.id}):`, e);
                }
            }
            
            // 2. 检查指定高亮 (从后往前，最后的优先，且优先于条件高亮)
            for (let i = this._specificHighlights.length - 1; i >= 0; i--) {
                const specHighlight = this._specificHighlights[i];
                if (specHighlight.cells.has(cell)) {
                    highlightInfo = {
                        type: 'specific',
                        id: specHighlight.id,
                        colors: specHighlight.colors,
                        colorIndex: specHighlight.colorIndex
                    };
                    break; // 找到就退出
                }
            }
            
            // 3. 应用高亮
            if (highlightInfo) {
                cellsToHighlight.set(cell, highlightInfo);
            }
            
            return false;
        });
        
        // 应用高亮
        cellsToHighlight.forEach((info, cell) => {
            this._applyHighlightToCell(cell, info);
        });
        
        // 启动动画定时器
        if (cellsToHighlight.size > 0) {
            this._startBorderTimer();
        }
    }

    /**
     * 对单个cell应用高亮
     * @param {object} cell - 要高亮的cell
     * @param {object} info - 高亮信息 {type, id, colors, colorIndex}
     */
    _applyHighlightToCell(cell, info) {
        const currentColor = info.colors[info.colorIndex];
        const hl = new mxCellHighlight(
            this.graph,
            currentColor,
            this.strokeWidth
        );
        hl.highlight(this.graph.view.getState(cell));
        
        this.highlights.set(cell, hl);
        this.cellsWithHighlight.add(cell);
        this._cellHighlightInfo.set(cell, info);
    }

    /**
     * 清除所有高亮但不影响高亮定义
     */
    _clearAllHighlights() {
        this.highlights.forEach(hl => hl.hide());
        this.highlights.clear();
        this.cellsWithHighlight.clear();
        this._cellHighlightInfo.clear();
    }

    setHighlightColors(colors) {
        if (Array.isArray(colors) && colors.length > 0) {
            this._borderColors = colors;
            this._colorIndex = 0; // 重置颜色索引
            // 兼容性：如果有高亮存在，更新颜色
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
        
        // 新增：清除所有高亮定义
        this._conditionalHighlights = [];
        this._specificHighlights = [];
        this._cellHighlightInfo.clear();
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
            // 更新旧系统的颜色索引（向后兼容）
            this._colorIndex = (this._colorIndex + 1) % this._borderColors.length;
            
            // 更新所有高亮组的颜色索引
            this._conditionalHighlights.forEach(highlight => {
                highlight.colorIndex = (highlight.colorIndex + 1) % highlight.colors.length;
            });
            this._specificHighlights.forEach(highlight => {
                highlight.colorIndex = (highlight.colorIndex + 1) % highlight.colors.length;
            });
            
            // 更新高亮显示
            this.cellsWithHighlight.forEach(cell => {
                const hl = this.highlights.get(cell);
                const info = this._cellHighlightInfo.get(cell);
                
                if (hl && info) {
                    // 使用新系统的颜色
                    const currentColor = info.colors[info.colorIndex];
                    hl.setHighlightColor(currentColor);
                    // 重新高亮以刷新颜色
                    hl.hide();
                    hl.highlight(this.graph.view.getState(cell));
                    
                    // 更新info中的colorIndex以保持同步
                    if (info.type === 'conditional') {
                        const condHighlight = this._conditionalHighlights.find(h => h.id === info.id);
                        if (condHighlight) {
                            info.colorIndex = condHighlight.colorIndex;
                        }
                    } else if (info.type === 'specific') {
                        const specHighlight = this._specificHighlights.find(h => h.id === info.id);
                        if (specHighlight) {
                            info.colorIndex = specHighlight.colorIndex;
                        }
                    }
                } else if (hl) {
                    // 向后兼容：使用旧的颜色系统
                    hl.setHighlightColor(this._getHighlightColor());
                    hl.hide();
                    hl.highlight(this.graph.view.getState(cell));
                }
            });
        }, this._interval);
    }

    /**
     * 自动高亮 alarm=1 的cell (向后兼容方法)
     * @param {function} callback - 判断回调函数
     * @param {number} intervalMs - 刷新间隔
     */
    startAutoHighlight(callback, intervalMs = 1000) {
        if (this._autoHighlightTimer) return;
        
        // 使用新系统添加一个默认的条件高亮
        this.addConditionalHighlight('_legacy_auto', callback, this._borderColors.slice());
        
        this._autoHighlightTimer = setInterval(() => {
            this._refreshHighlights();
        }, intervalMs);
    }
    
    stopAutoHighlight() {
        if (this._autoHighlightTimer) {
            clearInterval(this._autoHighlightTimer);
            this._autoHighlightTimer = null;
        }
        
        // 移除默认的条件高亮
        this.removeConditionalHighlight('_legacy_auto');
    }

    /**
     * 获取所有条件高亮的信息
     * @returns {Array} 条件高亮数组
     */
    getConditionalHighlights() {
        return this._conditionalHighlights.map(h => ({
            id: h.id,
            colors: h.colors.slice(),
            colorIndex: h.colorIndex
        }));
    }

    /**
     * 获取所有指定高亮的信息
     * @returns {Array} 指定高亮数组
     */
    getSpecificHighlights() {
        return this._specificHighlights.map(h => ({
            id: h.id,
            cells: Array.from(h.cells),
            colors: h.colors.slice(),
            colorIndex: h.colorIndex
        }));
    }

    /**
     * 立即刷新高亮显示
     */
    refresh() {
        this._refreshHighlights();
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
        
        // 将loadGraphXML函数添加到window.ohtoai下
        window.ohtoai.loadGraphXML = loadGraphXML;
        
        // 将编辑控制函数添加到window.ohtoai下
        window.ohtoai.enableEditing = enableEditing;
        window.ohtoai.disableEditing = disableEditing;
        window.ohtoai.isEditingEnabled = isEditingEnabled;

        // Add defensive fix for context menu in readonly mode
        const editorUi = window.sb.editorUi;
        if (editorUi && editorUi.menus) {
            const originalCreatePopupMenu = editorUi.menus.createPopupMenu;
            editorUi.menus.createPopupMenu = function(menu, cell, evt) {
                try {
                    // In readonly mode, clear selection before showing context menu to prevent firstChild errors
                    if (editorUi.editor && editorUi.editor.graph && !editorUi.editor.graph.isEnabled()) {
                        const graph = editorUi.editor.graph;
                        if (graph.getSelectionCount() > 0) {
                            console.log('Clearing selection before context menu in readonly mode');
                            graph.clearSelection();
                        }
                    }
                    return originalCreatePopupMenu.apply(this, arguments);
                } catch (error) {
                    console.error('Context menu creation error:', error);
                    // Clear selection if error occurs and try again
                    if (editorUi.editor && editorUi.editor.graph) {
                        editorUi.editor.graph.clearSelection();
                    }
                    try {
                        return originalCreatePopupMenu.apply(this, arguments);
                    } catch (secondError) {
                        console.error('Context menu creation failed twice:', secondError);
                        return; // Give up
                    }
                }
            };
        }

        setTimeout(() => {
            var url = "demo/manual.drawio.xml"; // 默认 URL
            if (url) {
                window.ohtoai.loadGraphXML(url, true).then(() => {
                    console.log("Diagram loaded, initializing StripedOverlayManager");
                    const graph = window.sb.editorUi.editor.graph;
                    window.ohtoai.stripedOverlayManager = new StripedOverlayManager(graph);
                    window.ohtoai.stripedOverlayManager.startAutoHighlight(cell => {
                        if (!cell || !cell.value) return false;
                        if (typeof cell.value === "string") return false;
                        return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                    });
                    // 如需手动停止高亮，可调用 manager.clearHighlight() 或 manager.stopAutoHighlight()
                }).catch(error => {
                    console.error("Failed to load diagram:", error);
                });
            }
        }, 1000);
    }, 120000);
});
