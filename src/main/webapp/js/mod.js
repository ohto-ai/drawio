/**
 * file: js/plugin.js
 * Description: This script loads a diagram from a URL specified in the query parameters.
 */


/**
 * 
 * @param {string} url 
 * @param {App} editorUi defaults to window.sb.editorUi
 */
function loadDiagramFromUrl(url, editorUi) {
    fetch(url)
        .then(resp => {
            // 获取文件名和其他信息
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
            editorUi = editorUi || window.sb.editorUi;
            var root = doc.documentElement;

            editorUi.editor.setGraphXml(root);

            editorUi.editor.setModified(false);

            var file = new LocalFile(editorUi, doc, fileName);
            editorUi.setCurrentFile(file);

            editorUi.updateDocumentTitle();
            editorUi.descriptorChanged();


            file.addListener(mxEvent.CHANGE, function(sender, evt){
                console.log('文件内容改变了');
            });

        });
}
/**
 * StripedOverlayManager
 * 基于 mxCellOverlay 为特定 cell 绘制红色透明斜纹
 */
/**
 * StripedOverlayManager（精简版）
 * 使用右下角 overlay 图标代替斜纹
 */
class StripedOverlayManager {
    constructor(graph, iconUrl = "img/lib/ibm/management/alert_notification.svg") {
        this.graph = graph;
        this.iconUrl = iconUrl;
        this.cellsWithOverlay = new Set();
        this._overlayMap = new Map();
    }

    /**
     * 创建 overlay
     */
    _createOverlay(cell, tooltip) {
        const overlay = new mxCellOverlay(
            new mxImage(this.iconUrl, 32, 32),
            tooltip || "警告"
        );

        // 可选点击事件
        overlay.addListener(mxEvent.CLICK, (sender, evt) => {
            console.log("点击了 cell: " + tooltip);
            evt.consume();
        });

        return overlay;
    }

    /**
     * 1. filterCells(callback)
     */
    filterCells(callback) {
        const result = [];
        this.graph.getModel().filterDescendants(cell => {
            if (callback(cell)) result.push(cell);
            return false;
        });
        return result;
    }

    /**
     * 2. applyOverlay(cells, tooltipFunc)
     */
    applyOverlay(cells, tooltipFunc = null) {
        cells.forEach(cell => {
            if (!this._overlayMap.has(cell)) {
                const tooltip = tooltipFunc ? tooltipFunc(cell) : "警告";
                const overlay = this._createOverlay(cell, tooltip);
                this._overlayMap.set(cell, overlay);
                this.graph.addCellOverlay(cell, overlay);
                this.cellsWithOverlay.add(cell);
            }
        });
    }

    /**
     * 3. clearOverlay()
     */
    clearOverlay() {
        this.cellsWithOverlay.forEach(cell => {
            this.graph.removeCellOverlays(cell);
        });
        this.cellsWithOverlay.clear();
        this._overlayMap.clear();
    }

    /**
     * 4. updateOverlay(callback, tooltipFunc)
     * callback(cell) => true 显示 overlay，false 移除
     */
    updateOverlay(callback, tooltipFunc = null) {
        const model = this.graph.getModel();
        model.filterDescendants(cell => {
            const shouldApply = callback(cell);
            const hasOverlay = this.cellsWithOverlay.has(cell);

            if (shouldApply && !hasOverlay) {
                const tooltip = tooltipFunc ? tooltipFunc(cell) : "警告";
                this.applyOverlay([cell], tooltipFunc);
            } else if (!shouldApply && hasOverlay) {
                this.graph.removeCellOverlays(cell);
                this.cellsWithOverlay.delete(cell);
                this._overlayMap.delete(cell);
            }
            return false;
        });
    }
}

// this.editor.getOrCreateFilename = function() {
//             var u = d.defaultFilename
//               , D = d.getCurrentFile();
//             null != D && (u = null != D.getTitle() ? D.getTitle() : u);
//             return u
//         }

// 高亮alarm属性为1的 cell
window.addEventListener("load", () => {
    setTimeout(() => {
        console.log("Plugin loaded: StripedOverlayManager");

        setTimeout(() => {
            var url = "demo/manual.drawio.xml"; // 默认 URL
            if (url) {
                loadDiagramFromUrl(url, window.sb.editorUi);

                console.log("Diagram loaded, initializing StripedOverlayManager");
                const graph = window.sb.editorUi.editor.graph;
                const manager = new StripedOverlayManager(graph);
                setInterval(() => {
                    manager.updateOverlay(
                        cell => {
                            if (!cell || !cell.value) return false;
                            if (typeof cell.value === "string") return false;
                            return cell.value.getAttribute && cell.value.getAttribute('alarm') === '1';
                        },
                        cell => {
                            if (!cell || !cell.value) return "";
                            if (typeof cell.value === "string") return "";
                            return "警告: " + cell.value.getAttribute('alarm');
                        }
                    );
                }, 1000);
            }
        }, 1000);

        // loadDiagramFromUrl("demo/manual.drawio.xml", window.sb.editorUi);


    }, 1000); // 延时 1 秒

});
