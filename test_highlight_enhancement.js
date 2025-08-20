/**
 * Simple test script to verify the enhanced highlighting functionality
 * This can be run in the browser console to test the new features
 */

function testHighlightEnhancements() {
    console.log("Testing Enhanced Highlighting Functionality...");
    
    // Check if the manager exists
    if (!window.ohtoai?.stripedOverlayManager) {
        console.error("StripedOverlayManager not found!");
        return false;
    }
    
    const manager = window.ohtoai.stripedOverlayManager;
    const graph = window.sb.editorUi.editor.graph;
    
    // Get some test cells
    const cells = [];
    const model = graph.getModel();
    model.filterDescendants(cell => {
        if (graph.model.isVertex(cell) || graph.model.isEdge(cell)) {
            cells.push(cell);
        }
        return false;
    });
    
    if (cells.length === 0) {
        console.error("No cells found for testing!");
        return false;
    }
    
    console.log(`Found ${cells.length} cells for testing`);
    
    try {
        // Test 1: Add conditional highlight
        console.log("Test 1: Adding conditional highlight...");
        const success1 = manager.addConditionalHighlight(
            'test_conditional_1',
            (cell) => {
                // Highlight cells with "test" in their value
                if (!cell || !cell.value) return false;
                const label = graph.getLabel(cell);
                return label && label.toLowerCase().includes('test');
            },
            ['#ff0000', '#00ff00']
        );
        console.log("Conditional highlight added:", success1);
        
        // Test 2: Add specific highlight
        console.log("Test 2: Adding specific highlight...");
        const testCells = cells.slice(0, Math.min(2, cells.length));
        const success2 = manager.addSpecificHighlight(
            'test_specific_1',
            testCells,
            ['#0000ff', '#ffff00']
        );
        console.log("Specific highlight added:", success2);
        
        // Test 3: Refresh highlights
        console.log("Test 3: Refreshing highlights...");
        manager.refresh();
        
        // Test 4: Get highlight info
        console.log("Test 4: Getting highlight information...");
        const conditionalHighlights = manager.getConditionalHighlights();
        const specificHighlights = manager.getSpecificHighlights();
        console.log("Conditional highlights:", conditionalHighlights);
        console.log("Specific highlights:", specificHighlights);
        
        // Test 5: Priority test - add overlapping highlights
        console.log("Test 5: Testing priority system...");
        if (testCells.length > 0) {
            // Add another specific highlight that overlaps
            manager.addSpecificHighlight(
                'test_specific_2',
                [testCells[0]], // Same cell as before
                ['#ff00ff', '#00ffff'] // Different colors
            );
            manager.refresh();
            console.log("Overlapping highlight added - should use newer colors");
        }
        
        console.log("All tests completed successfully!");
        
        // Schedule cleanup
        setTimeout(() => {
            console.log("Cleaning up test highlights...");
            manager.removeConditionalHighlight('test_conditional_1');
            manager.removeSpecificHighlight('test_specific_1');
            manager.removeSpecificHighlight('test_specific_2');
            manager.refresh();
            console.log("Test cleanup completed");
        }, 5000);
        
        return true;
        
    } catch (error) {
        console.error("Test failed with error:", error);
        return false;
    }
}

// Export test function
if (typeof window !== 'undefined') {
    window.testHighlightEnhancements = testHighlightEnhancements;
}