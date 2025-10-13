/**
 * @file mod.js
 * @brief DrawIO图表加载和高亮管理模块
 * @description 此脚本提供DrawIO图表文件的加载功能和条纹覆盖高亮管理器
 */

/**
 * @brief 加载DrawIO图表文件
 * @param {string} url - 文件的URL地址
 * @param {boolean} readonly - 是否以只读模式加载，默认为false
 * @returns {Promise<LocalFile>} 返回加载的LocalFile对象的Promise
 * @throws {Error} 当editorUi不可用或文件加载失败时抛出异常
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
 * @brief 从服务器加载指定的图表文件
 * @param {string} filename - 服务器上的文件名
 * @returns {Promise<LocalFile>} 返回加载的LocalFile对象的Promise
 * @description 通过/open/接口从服务器加载指定的图表文件
 */
function loadServerFile(filename) {
    console.log(`loadServerFile: Loading server file ${filename}`);
    
    return new Promise((resolve, reject) => {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/open/' + encodeURIComponent(filename), true);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        const editorUi = window.sb && window.sb.editorUi;
                        if (!editorUi) {
                            throw new Error('editorUi not available');
                        }
                        
                        // 创建LocalFile实例
                        const localFile = new LocalFile(editorUi, xhr.responseText, filename, true);
                        
                        // 使用editorUi的fileLoaded方法来加载文件
                        editorUi.fileLoaded(localFile);
                        
                        console.log(`loadServerFile: Server file ${filename} loaded successfully`);
                        resolve(localFile);
                        
                    } catch (error) {
                        console.error(`loadServerFile: Error processing server file ${filename}:`, error);
                        reject(error);
                    }
                } else {
                    const error = new Error(`Failed to load server file: ${xhr.status} ${xhr.statusText}`);
                    console.error(`loadServerFile: ${error.message}`);
                    reject(error);
                }
            }
        };
        xhr.send();
    });
}

/**
 * @brief 从URL hash中提取服务器文件名
 * @returns {string|null} 返回服务器文件名，如果没有则返回null
 */
function getServerFileFromHash() {
    var hash = window.location.hash;
    if (hash && hash.includes('#Lserver:')) {
        var match = hash.match(/#Lserver:([^&]+)/);
        if (match && match[1]) {
            return decodeURIComponent(match[1]);
        }
    }
    return null;
}

/**
 * @brief 启用图表编辑功能
 * @returns {boolean} 启用成功返回true，失败返回false
 * @description 启用图形编辑和文件编辑功能，使图表可以被修改
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
 * @brief 禁用图表编辑功能，设置为只读模式
 * @returns {boolean} 禁用成功返回true，失败返回false
 * @description 禁用图形编辑和文件编辑功能，使图表变为只读模式
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
 * @brief 检查当前图表编辑状态
 * @returns {boolean} 编辑功能启用时返回true，否则返回false
 * @description 检查图形和文件的编辑状态，两者都启用时才返回true
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
 * @class StripedOverlayManager
 * @brief 条纹覆盖高亮管理器
 * @description 基于mxCellHighlight实现的多重高亮管理器，支持条件高亮和指定高亮两种模式
 * 
 * 特性：
 * - 条件高亮：基于回调函数的动态评估高亮
 * - 指定高亮：直接指定单元格的高亮
 * - 优先级系统：指定高亮优先于条件高亮，后添加的高亮优先于早添加的
 * - 独立颜色循环：每个高亮组独立管理颜色动画
 * - 不修改原始样式：使用覆盖层实现高亮效果
 */
class StripedOverlayManager {
    /**
     * @brief 构造函数
     * @param {mxGraph} graph - mxGraph实例
     * @param {number} strokeWidth - 高亮边框宽度，默认为4
     */
    constructor(graph, strokeWidth = 4) {
        this.graph = graph;
        this.strokeWidth = strokeWidth;
        this.cellsWithHighlight = new Set();
        this.highlights = new Map();
        this._borderTimer = null;
        this._interval = 300;
        
        // 多个条件高亮支持
        this._conditionalHighlights = [];  // [{id, callback, colors, colorIndex}]
        
        // 多个指定高亮支持  
        this._specificHighlights = [];     // [{id, cells, colors, colorIndex}]
        
        // 追踪每个cell的高亮信息 {cell -> {type, id, highlight}}
        this._cellHighlightInfo = new Map();
    }

    /**
     * @brief 添加条件高亮
     * @param {string} id - 高亮标识符，用于后续移除或更新
     * @param {function} callback - 判断函数，接受cell参数，返回boolean
     * @param {string[]} colors - 颜色组数组，用于循环动画显示
     * @returns {boolean} 添加成功返回true，参数无效返回false
     * @description 添加基于条件判断的动态高亮，满足条件的单元格将被高亮显示
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
     * @brief 移除条件高亮
     * @param {string} id - 要移除的高亮标识符
     * @returns {boolean} 移除成功返回true，未找到对应高亮返回false
     * @description 根据标识符移除对应的条件高亮，并刷新显示
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
     * @brief 添加指定高亮
     * @param {string} id - 高亮标识符，用于后续移除或更新
     * @param {object[]} cells - 要高亮的单元格数组
     * @param {string[]} colors - 颜色组数组，用于循环动画显示
     * @returns {boolean} 添加成功返回true，参数无效返回false
     * @description 为指定的单元格添加高亮，指定高亮优先级高于条件高亮
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
     * @brief 移除指定高亮
     * @param {string} id - 要移除的高亮标识符
     * @returns {boolean} 移除成功返回true，未找到对应高亮返回false
     * @description 根据标识符移除对应的指定高亮，并刷新显示
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
     * @brief 刷新所有高亮显示
     * @description 重新计算所有高亮条件并应用高亮效果，用于手动刷新显示状态
     * @private
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
     * @brief 对单个单元格应用高亮效果
     * @param {object} cell - 要高亮的单元格
     * @param {object} info - 高亮信息对象，包含type、id、colors、colorIndex等属性
     * @description 为指定单元格创建mxCellHighlight实例并应用高亮
     * @private
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
     * @brief 清除所有高亮显示但不删除高亮定义
     * @description 清除当前显示的所有高亮效果，但保留高亮配置以便后续刷新
     * @private
     */
    _clearAllHighlights() {
        this.highlights.forEach(hl => hl.hide());
        this.highlights.clear();
        this.cellsWithHighlight.clear();
        this._cellHighlightInfo.clear();
    }

    /**
     * @brief 完全清除所有高亮
     * @description 停止动画定时器，清除所有高亮显示，并删除所有高亮定义
     */
    clearHighlight() {
        if (this._borderTimer) {
            clearInterval(this._borderTimer);
            this._borderTimer = null;
        }
        this.highlights.forEach(hl => hl.hide());
        this.highlights.clear();
        this.cellsWithHighlight.clear();
        
        // 清除所有高亮定义
        this._conditionalHighlights = [];
        this._specificHighlights = [];
        this._cellHighlightInfo.clear();
    }

    /**
     * @brief 启动边框动画定时器
     * @description 启动定时器以实现高亮边框的颜色循环动画效果
     * @private
     */
    // 启动蚂蚁线定时器
    _startBorderTimer() {
        if (this._borderTimer) return;
        this._borderTimer = setInterval(() => {
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
                }
            });
        }, this._interval);
    }

    /**
     * @brief 获取所有条件高亮信息
     * @returns {Array} 包含条件高亮配置的数组，每个元素包含id、colors、colorIndex等属性
     * @description 返回当前所有条件高亮的配置信息副本，不包含回调函数
     */
    getConditionalHighlights() {
        return this._conditionalHighlights.map(h => ({
            id: h.id,
            colors: h.colors.slice(),
            colorIndex: h.colorIndex
        }));
    }

    /**
     * @brief 获取所有指定高亮信息
     * @returns {Array} 包含指定高亮配置的数组，每个元素包含id、cells、colors、colorIndex等属性
     * @description 返回当前所有指定高亮的配置信息副本
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
     * @brief 立即刷新高亮显示
     * @description 手动触发高亮刷新，重新计算所有条件并更新显示
     */
    refresh() {
        this._refreshHighlights();
    }
}

/**
 * @brief 服务器保存功能
 * @description 将文件保存到服务器，而不是客户端下载
 */
function saveToServer(filename, success, error) {
    console.log('saveToServer: Saving file to server', { filename });
    
    try {
        const editorUi = window.sb && window.sb.editorUi;
        if (!editorUi) {
            throw new Error('editorUi not available');
        }
        
        const currentFile = editorUi.getCurrentFile();
        if (!currentFile) {
            throw new Error('No current file to save');
        }
        
        // Ensure the graph changes are synced to file data before saving
        if (editorUi.editor && editorUi.editor.graph) {
            const graph = editorUi.editor.graph;
            
            // Force update file data with current graph state
            try {
                // Get the current XML representation of the graph
                const enc = new mxCodec(mxUtils.createXmlDocument());
                const node = enc.encode(graph.getModel());
                const xml = mxUtils.getPrettyXml(node);
                
                // Update the file data with current graph state
                currentFile.setData(xml);
                console.log('saveToServer: Graph state synced to file data');
            } catch (syncError) {
                console.warn('saveToServer: Failed to sync graph state, using existing file data:', syncError);
            }
        }
        
        // Get the file data (XML content)
        const fileData = currentFile.getData();
        if (!fileData) {
            throw new Error('No data to save');
        }
        
        // Prepare the filename
        let saveFilename = filename || currentFile.getTitle() || 'untitled';
        if (!saveFilename.endsWith('.xml') && !saveFilename.endsWith('.drawio')) {
            saveFilename += '.drawio';
        }
        
        // Prepare request data
        const requestData = {
            filename: saveFilename,
            content: fileData
        };
        
        // Send to server
        fetch('/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('saveToServer: File saved successfully', data);
                
                // Mark file as not modified since it's saved
                currentFile.setModified(false);
                
                // Show success message
                if (editorUi.editor && editorUi.editor.graph) {
                    editorUi.editor.setStatus('文件已保存到服务器: ' + data.filename);
                }
                
                if (success) {
                    success(data);
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        })
        .catch(err => {
            console.error('saveToServer: Error saving file', err);
            
            // Show error message
            if (editorUi.editor && editorUi.editor.graph) {
                editorUi.editor.setStatus('保存失败: ' + err.message);
            }
            
            if (error) {
                error(err);
            }
        });
        
    } catch (err) {
        console.error('saveToServer: Error preparing save', err);
        if (error) {
            error(err);
        }
    }
}

/**
 * @brief 模块初始化入口
 * @description 等待页面加载完成后初始化高亮管理器和相关功能
 */
// Override Menus.prototype.createMenubar to remove Help menu properly
function removeHelpMenuFromMenubar() {
    if (typeof Menus !== 'undefined' && Menus.prototype && Menus.prototype.createMenubar) {
        // Store original createMenubar function
        const originalCreateMenubar = Menus.prototype.createMenubar;
        
        // Override createMenubar to exclude help menu
        Menus.prototype.createMenubar = function(container) {
            // Create a modified version of defaultMenuItems without 'help'
            const originalDefaultItems = this.defaultMenuItems;
            let modifiedItems;
            
            if (typeof originalDefaultItems === 'string') {
                modifiedItems = originalDefaultItems.split(' ').filter(item => item !== 'help');
            } else if (Array.isArray(originalDefaultItems)) {
                modifiedItems = originalDefaultItems.filter(item => item !== 'help');
            } else {
                // Fallback
                modifiedItems = ["file", "edit", "view", "arrange", "extras"];
            }
            
            // Temporarily override defaultMenuItems for this call
            this.defaultMenuItems = modifiedItems;
            
            // Call original createMenubar
            const result = originalCreateMenubar.call(this, container);
            
            // Restore original defaultMenuItems
            this.defaultMenuItems = originalDefaultItems;
            
            console.log("Help menu removed from menubar during creation");
            return result;
        };
        
        return true;
    }
    return false;
}

// Try to remove Help menu immediately if Menus is available
if (!removeHelpMenuFromMenubar()) {
    // If not available yet, set up polling to catch it when it loads
    let attempts = 0;
    const maxAttempts = 50; // Poll for up to 5 seconds
    const pollForMenus = setInterval(() => {
        attempts++;
        if (removeHelpMenuFromMenubar() || attempts >= maxAttempts) {
            clearInterval(pollForMenus);
        }
    }, 100);
}

window.addEventListener("load", () => {
    window.ohtoai = window.ohtoai || {};

    /**
     * @brief 等待editorUi初始化完成
     * @param {function} callback - 初始化完成后的回调函数
     * @param {number} timeout - 超时时间，默认10秒
     * @description 轮询检查editorUi是否已创建，创建完成后执行回调
     */
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
        console.log("高亮管理器插件已加载");
        
        // 注册图表加载功能到全局对象
        window.ohtoai.loadGraphXML = loadGraphXML;
        
        // 注册服务器文件加载功能到全局对象
        window.ohtoai.loadServerFile = loadServerFile;
        window.ohtoai.getServerFileFromHash = getServerFileFromHash;
        
        // 注册编辑控制功能到全局对象
        window.ohtoai.enableEditing = enableEditing;
        window.ohtoai.disableEditing = disableEditing;
        window.ohtoai.isEditingEnabled = isEditingEnabled;
        
        // 注册服务器保存功能到全局对象
        window.ohtoai.saveToServer = saveToServer;
        
        const editorUi = window.sb.editorUi;
        
        // 修改文件菜单，移除客户端保存选项，添加服务器保存功能
        if (editorUi && editorUi.menus) {
            const fileMenu = editorUi.menus.get('file');
            if (fileMenu) {
                const originalFunct = fileMenu.funct;
                
                fileMenu.funct = function(menu, parent) {
                    console.log('修改文件菜单：移除客户端保存选项');
                    
                    // 添加基本的文件操作，但移除saveAs和exportAs
                    editorUi.menus.addMenuItems(menu, ['new', 'open'], parent);
                    
                    // 添加分隔符
                    menu.addSeparator(parent);
                    
                    // 添加服务器保存功能
                    menu.addItem('保存到服务器', null, function() {
                        const currentFile = editorUi.getCurrentFile();
                        if (!currentFile) {
                            editorUi.alert('没有文件可保存');
                            return;
                        }
                        
                        let filename = currentFile.getTitle();
                        if (!filename || filename === 'Untitled') {
                            filename = prompt('请输入文件名:', 'diagram');
                            if (!filename) {
                                return; // 用户取消
                            }
                        }
                        
                        saveToServer(filename, 
                            function(data) {
                                editorUi.alert('文件保存成功: ' + data.filename);
                            },
                            function(err) {
                                editorUi.alert('保存失败: ' + err.message);
                            }
                        );
                    }, parent);
                    
                    // 添加分隔符
                    menu.addSeparator(parent);
                    
                    // 只保留导入功能，移除导出功能以防止用户保存到客户端
                    editorUi.menus.addMenuItems(menu, ['import'], parent);
                    
                    // 添加分隔符
                    menu.addSeparator(parent);
                    
                    // 添加库功能
                    editorUi.menus.addMenuItems(menu, ['newLibrary', 'openLibrary'], parent);
                    
                    // 添加其他必要的文件菜单项，但排除保存到客户端的功能
                    const currentFile = editorUi.getCurrentFile();
                    if (currentFile && editorUi.fileNode) {
                        const filename = currentFile.getTitle() || editorUi.defaultFilename;
                        if (!/(\\.html)$/i.test(filename) && !/(\\.svg)$/i.test(filename)) {
                            editorUi.menus.addMenuItems(menu, ['-', 'properties'], parent);
                        }
                    }
                    
                    // 添加页面设置和打印，但移除保存相关的功能
                    editorUi.menus.addMenuItems(menu, ['-', 'pageSetup', 'print'], parent);
                    
                    // 保留关闭和退出功能
                    editorUi.menus.addMenuItems(menu, ['-', 'close', '-', 'exit'], parent);
                };
            }
            
            // 重写保存操作以使用服务器保存
            if (editorUi.actions) {
                const saveAction = editorUi.actions.get('save');
                if (saveAction) {
                    const originalSaveFunct = saveAction.funct;
                    saveAction.funct = function() {
                        console.log('拦截保存操作，使用服务器保存');
                        const currentFile = editorUi.getCurrentFile();
                        if (!currentFile) {
                            editorUi.alert('没有文件可保存');
                            return;
                        }
                        
                        let filename = currentFile.getTitle() || 'untitled';
                        saveToServer(filename, 
                            function(data) {
                                console.log('保存成功:', data.filename);
                            },
                            function(err) {
                                console.error('保存失败:', err.message);
                                editorUi.alert('保存失败: ' + err.message);
                            }
                        );
                    };
                }
            }
        }

        // Remove library-related menu items and fix context menu issues
        if (editorUi && editorUi.menus) {
            // Remove library-related options from file menu
            const originalFileMenu = editorUi.menus.get('file');
            if (originalFileMenu) {
                const originalFileMenuFunc = originalFileMenu.funct;
                originalFileMenu.funct = function(menu, parent) {
                    // Call original file menu function
                    originalFileMenuFunc.apply(this, arguments);
                    
                    // Remove library-related menu items
                    const menuItems = menu.div ? menu.div.querySelectorAll('.geMenuItem') : [];
                    menuItems.forEach(function(item) {
                        const text = item.textContent || '';
                        // Remove "New Library" and "Open Library From" related options
                        if (text.includes('Library') || text.includes('library')) {
                            item.style.display = 'none';
                        }
                    });
                };
            }
            
            // Context menu defensive fix for readonly mode
            const originalCreatePopupMenu = editorUi.menus.createPopupMenu;
            editorUi.menus.createPopupMenu = function(menu, cell, evt) {
                try {
                    // Clear selection before showing context menu in readonly mode to prevent firstChild error
                    if (editorUi.editor && editorUi.editor.graph && !editorUi.editor.graph.isEnabled()) {
                        const graph = editorUi.editor.graph;
                        if (graph.getSelectionCount() > 0) {
                            graph.clearSelection();
                        }
                    }
                    return originalCreatePopupMenu.apply(this, arguments);
                } catch (error) {
                    console.error('Context menu creation error:', error);
                    // If error occurs, clear selection and retry
                    if (editorUi.editor && editorUi.editor.graph) {
                        editorUi.editor.graph.clearSelection();
                    }
                    try {
                        return originalCreatePopupMenu.apply(this, arguments);
                    } catch (secondError) {
                        console.error('Context menu creation second failure:', secondError);
                        return; // Give up processing
                    }
                }
            };
        }

        // 添加服务器库加载API
        window.ohtoai = window.ohtoai || {};
        window.ohtoai.loadLibraryFromServer = function(libraryPath, successCallback, errorCallback) {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', '/library/' + encodeURIComponent(libraryPath), true);
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4) {
                    if (xhr.status === 200) {
                        try {
                            const libraryXML = xhr.responseText;
                            const doc = mxUtils.parseXml(libraryXML);
                            const library = doc.documentElement;
                            
                            if (library.nodeName === 'mxlibrary') {
                                // 解析库并添加到侧边栏
                                const shapes = JSON.parse(library.textContent || '[]');
                                const title = library.getAttribute('title') || libraryPath;
                                
                                // 获取侧边栏实例
                                const sidebar = editorUi.sidebar;
                                if (sidebar && sidebar.addLibraryEntries) {
                                    sidebar.addLibraryEntries(shapes, title);
                                    console.log('成功加载库:', title, '包含', shapes.length, '个形状');
                                    
                                    if (successCallback) {
                                        successCallback({
                                            title: title,
                                            shapesCount: shapes.length,
                                            library: library
                                        });
                                    }
                                } else {
                                    throw new Error('侧边栏不可用');
                                }
                            } else {
                                throw new Error('无效的库文件格式');
                            }
                        } catch (e) {
                            console.error('解析库文件失败:', e);
                            if (errorCallback) {
                                errorCallback({ message: '解析库文件失败: ' + e.message });
                            }
                        }
                    } else {
                        console.error('加载库文件失败:', xhr.status, xhr.statusText);
                        if (errorCallback) {
                            errorCallback({ 
                                message: '加载库文件失败: ' + xhr.status + ' ' + xhr.statusText 
                            });
                        }
                    }
                }
            };
            xhr.send();
        };

        // 延迟初始化默认图表和高亮管理器
        setTimeout(() => {
            // 检查URL中是否有服务器文件标识符
            var hash = window.location.hash;
            var isServerFile = hash && hash.includes('#Lserver:');
            var hasFileParam = hash && (hash.includes('#L') || isServerFile);
            
            // 只有在没有文件加载参数时才加载默认demo文件
            if (!hasFileParam) {
                var url = "demo/BP-2B型微机母线保护原理图.drawio.xml"; // 默认图表文件
                if (url) {
                    window.ohtoai.loadGraphXML(url, true).then(() => {
                        console.log("图表已加载，正在初始化高亮管理器");
                        const graph = window.sb.editorUi.editor.graph;
                        window.ohtoai.stripedOverlayManager = new StripedOverlayManager(graph);
                        // 初始化告警单元格的条件高亮
                        window.ohtoai.stripedOverlayManager.addConditionalHighlight('alarm_cells', cell => {
                            if (!cell || !cell.value) return false;
                            if (typeof cell.value === "string") return false;
                            return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                        }, ['#ff0000', '#ffff00']);
                        window.ohtoai.stripedOverlayManager.refresh();
                    }).catch(error => {
                        console.error("图表加载失败:", error);
                    });
                }
            } else {
                // 如果有服务器文件参数，先尝试加载服务器文件
                var serverFilename = window.ohtoai.getServerFileFromHash();
                if (serverFilename) {
                    console.log("检测到服务器文件参数:", serverFilename, "正在加载...");
                    
                    // 等待editorUi准备就绪，然后加载服务器文件
                    var loadServerFileWhenReady = function() {
                        if (window.sb && window.sb.editorUi && window.sb.editorUi.editor) {
                            window.ohtoai.loadServerFile(serverFilename).then(() => {
                                console.log("服务器文件已加载，正在初始化高亮管理器");
                                const graph = window.sb.editorUi.editor.graph;
                                window.ohtoai.stripedOverlayManager = new StripedOverlayManager(graph);
                                // 初始化告警单元格的条件高亮
                                window.ohtoai.stripedOverlayManager.addConditionalHighlight('alarm_cells', cell => {
                                    if (!cell || !cell.value) return false;
                                    if (typeof cell.value === "string") return false;
                                    return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                                }, ['#ff0000', '#ffff00']);
                                window.ohtoai.stripedOverlayManager.refresh();
                            }).catch(error => {
                                console.error("服务器文件加载失败:", error);
                                // 加载失败时初始化基础高亮管理器
                                if (window.sb && window.sb.editorUi && window.sb.editorUi.editor && window.sb.editorUi.editor.graph) {
                                    const graph = window.sb.editorUi.editor.graph;
                                    window.ohtoai.stripedOverlayManager = new StripedOverlayManager(graph);
                                    window.ohtoai.stripedOverlayManager.refresh();
                                }
                            });
                        } else {
                            setTimeout(loadServerFileWhenReady, 500);
                        }
                    };
                    loadServerFileWhenReady();
                } else {
                    console.log("检测到文件加载参数，跳过默认demo文件，等待文件加载后初始化高亮管理器");
                    
                    // 等待文件加载完成后初始化高亮管理器
                    var checkInterval = setInterval(() => {
                        if (window.sb && window.sb.editorUi && window.sb.editorUi.editor && window.sb.editorUi.editor.graph) {
                            const graph = window.sb.editorUi.editor.graph;
                            const currentFile = window.sb.editorUi.getCurrentFile();
                            if (currentFile) {
                                console.log("文件已加载，正在初始化高亮管理器");
                                window.ohtoai.stripedOverlayManager = new StripedOverlayManager(graph);
                                // 初始化告警单元格的条件高亮
                                window.ohtoai.stripedOverlayManager.addConditionalHighlight('alarm_cells', cell => {
                                    if (!cell || !cell.value) return false;
                                    if (typeof cell.value === "string") return false;
                                    return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                                }, ['#ff0000', '#ffff00']);
                                window.ohtoai.stripedOverlayManager.refresh();
                                clearInterval(checkInterval);
                            }
                        }
                    }, 500); // 检查间隔500ms
                    
                    // 10秒后停止检查，防止无限循环
                    setTimeout(() => {
                        clearInterval(checkInterval);
                        console.log("等待文件加载超时，初始化基础高亮管理器");
                        if (window.sb && window.sb.editorUi && window.sb.editorUi.editor && window.sb.editorUi.editor.graph) {
                            const graph = window.sb.editorUi.editor.graph;
                            window.ohtoai.stripedOverlayManager = new StripedOverlayManager(graph);
                            window.ohtoai.stripedOverlayManager.addConditionalHighlight('alarm_cells', cell => {
                                if (!cell || !cell.value) return false;
                                if (typeof cell.value === "string") return false;
                                return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                            }, ['#ff0000', '#ffff00']);
                            window.ohtoai.stripedOverlayManager.refresh();
                        }
                    }, 10000);
                }
            }
        }, 1000);
    }, 120000);
});
