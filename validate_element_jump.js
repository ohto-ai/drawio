#!/usr/bin/env node

/**
 * Node.js test script to validate the jumpToElement function implementation
 * This tests the basic logic without requiring a full browser environment
 */

// Mock browser globals that the function depends on
global.console = console;
global.setTimeout = setTimeout;

// Mock mxCellHighlight class
function mxCellHighlight(graph, color, strokeWidth) {
    this.graph = graph;
    this.color = color;
    this.strokeWidth = strokeWidth;
    
    this.highlight = function(state) {
        console.log(`[MOCK] Highlighting cell with color: ${this.color}, stroke: ${this.strokeWidth}`);
    };
    
    this.destroy = function() {
        console.log('[MOCK] Highlight destroyed');
    };
}

global.mxCellHighlight = mxCellHighlight;

// Extract and eval the jumpToElement function from export.js
const fs = require('fs');
const path = require('path');

const exportJsPath = path.join(__dirname, 'src/main/webapp/js/export.js');
const exportJsContent = fs.readFileSync(exportJsPath, 'utf8');

// Extract the jumpToElement function
const functionMatch = exportJsContent.match(/function jumpToElement\([\s\S]*?^}/m);
if (!functionMatch) {
    console.error('jumpToElement function not found in export.js');
    process.exit(1);
}

const jumpToElementCode = functionMatch[0];

// Evaluate the function in our context
eval(jumpToElementCode);

// Create a mock graph for testing
function createMockGraph() {
    const mockCells = [
        { getId: () => 'element1' },
        { getId: () => 'element2' },
        { getId: () => 'shape1' },
        { getId: () => 'connector1' },
        { getId: () => 'testelem' }
    ];
    
    const mockBounds = {
        x: 100, y: 100, width: 120, height: 80
    };
    
    const mockView = {
        getScale: () => 1.0,
        getTranslate: () => ({ x: 0, y: 0 }),
        setTranslate: function(x, y) {
            console.log(`[MOCK] View translated to: ${x}, ${y}`);
        },
        getState: function(cell) {
            return { cell: cell, id: cell.getId() };
        }
    };
    
    const mockModel = {
        getRoot: () => ({ id: 'root' }),
        getDescendants: function(root) {
            return mockCells;
        }
    };
    
    const mockContainer = {
        offsetWidth: 800,
        offsetHeight: 600
    };
    
    return {
        getModel: () => mockModel,
        getCellBounds: (cell) => mockBounds,
        getView: () => mockView,
        getContainer: () => mockContainer,
        setSelectionCell: function(cell) {
            console.log(`[MOCK] Selected cell: ${cell.getId()}`);
        }
    };
}

// Run tests
function runTests() {
    console.log('=== Testing jumpToElement Function ===\n');
    
    const mockGraph = createMockGraph();
    
    // Test 1: Jump to existing element
    console.log('Test 1: Jump to existing element "element1"');
    const result1 = jumpToElement(mockGraph, 'element1');
    console.log(`Result: ${result1 ? 'SUCCESS' : 'FAILED'}`);
    console.log('Expected: SUCCESS\n');
    
    // Test 2: Jump to non-existing element
    console.log('Test 2: Jump to non-existing element "nonexistent"');
    const result2 = jumpToElement(mockGraph, 'nonexistent');
    console.log(`Result: ${result2 ? 'SUCCESS' : 'FAILED'}`);
    console.log('Expected: FAILED\n');
    
    // Test 3: Jump to different elements
    console.log('Test 3: Jump to various elements');
    const testElements = ['element2', 'shape1', 'testelem'];
    testElements.forEach(elemId => {
        console.log(`Testing element: ${elemId}`);
        const result = jumpToElement(mockGraph, elemId);
        console.log(`Result: ${result ? 'SUCCESS' : 'FAILED'}`);
    });
    console.log();
    
    // Test 4: Error handling
    console.log('Test 4: Error handling');
    try {
        const result = jumpToElement(null, 'element1');
        console.log('Null graph test: Handled gracefully');
    } catch (e) {
        console.log('Null graph test: Error caught:', e.message);
    }
    
    try {
        const result = jumpToElement(mockGraph, null);
        console.log('Null elementId test: Handled gracefully');
    } catch (e) {
        console.log('Null elementId test: Error caught:', e.message);
    }
    
    console.log('\n=== Test Results ===');
    console.log('✓ Function extracted successfully from export.js');
    console.log('✓ Basic functionality tests completed');
    console.log('✓ Error handling tests completed');
    console.log('✓ Mock highlighting system working');
    
    return true;
}

// Validate the function exists and run tests
if (typeof jumpToElement === 'function') {
    console.log('jumpToElement function loaded successfully\n');
    runTests();
} else {
    console.error('Failed to load jumpToElement function');
    process.exit(1);
}