/**
 * Test script for element jump functionality
 * This script tests the jumpToElement function with various scenarios
 */

// Mock graph and related functions for testing
function createMockGraph() {
    var mockCells = [
        { getId: () => 'element1', value: 'Rectangle 1' },
        { getId: () => 'element2', value: 'Rectangle 2' },
        { getId: () => 'shape1', value: 'Circle' },
        { getId: () => 'connector1', value: '' },
        { getId: () => 'testelem', value: 'Test Element' }
    ];
    
    var mockBounds = {
        x: 100, y: 100, width: 120, height: 80
    };
    
    var mockView = {
        getScale: () => 1.0,
        getTranslate: () => ({ x: 0, y: 0 }),
        setTranslate: function(x, y) {
            console.log('View translated to:', x, y);
        }
    };
    
    var mockModel = {
        getRoot: () => ({ id: 'root' }),
        getDescendants: function(root) {
            return mockCells;
        }
    };
    
    var mockContainer = {
        offsetWidth: 800,
        offsetHeight: 600
    };
    
    return {
        getModel: () => mockModel,
        getCellBounds: (cell) => mockBounds,
        getView: () => mockView,
        getContainer: () => mockContainer,
        setSelectionCell: function(cell) {
            console.log('Selected cell:', cell.getId());
        }
    };
}

// Mock mxCellHighlight class
function mxCellHighlight(graph, color, strokeWidth) {
    this.graph = graph;
    this.color = color;
    this.strokeWidth = strokeWidth;
    
    this.highlight = function(state) {
        console.log('Highlighting cell with color:', this.color, 'stroke:', this.strokeWidth);
    };
    
    this.destroy = function() {
        console.log('Highlight destroyed');
    };
}

// Test the jumpToElement function
function runTests() {
    console.log('=== Testing Element Jump Functionality ===\n');
    
    var mockGraph = createMockGraph();
    
    // Test 1: Jump to existing element
    console.log('Test 1: Jump to existing element "element1"');
    var result1 = jumpToElement(mockGraph, 'element1');
    console.log('Result:', result1 ? 'SUCCESS' : 'FAILED');
    console.log('Expected: SUCCESS\n');
    
    // Test 2: Jump to non-existing element
    console.log('Test 2: Jump to non-existing element "nonexistent"');
    var result2 = jumpToElement(mockGraph, 'nonexistent');
    console.log('Result:', result2 ? 'SUCCESS' : 'FAILED');
    console.log('Expected: FAILED\n');
    
    // Test 3: Jump to different elements
    console.log('Test 3: Jump to various elements');
    var testElements = ['element2', 'shape1', 'testelem'];
    testElements.forEach(function(elemId) {
        console.log('Testing element:', elemId);
        var result = jumpToElement(mockGraph, elemId);
        console.log('Result:', result ? 'SUCCESS' : 'FAILED');
    });
    console.log();
    
    // Test 4: Error handling with null parameters
    console.log('Test 4: Error handling');
    try {
        jumpToElement(null, 'element1');
        console.log('Null graph test: Should have failed but didn\'t');
    } catch (e) {
        console.log('Null graph test: Properly handled error');
    }
    
    try {
        jumpToElement(mockGraph, null);
        console.log('Null elementId test: Handled gracefully');
    } catch (e) {
        console.log('Null elementId test: Error occurred');
    }
    
    console.log('\n=== Test Summary ===');
    console.log('All tests completed. Check the console output above for detailed results.');
    console.log('The jumpToElement function should:');
    console.log('- Return true when element is found and successfully navigated to');
    console.log('- Return false when element is not found');
    console.log('- Handle errors gracefully');
    console.log('- Center the view on the target element');
    console.log('- Highlight the target element temporarily');
}

// URL parameter parsing test
function testUrlParameterParsing() {
    console.log('\n=== Testing URL Parameter Parsing ===');
    
    // Mock URL parameters for testing
    var testUrls = [
        'http://localhost:8090/?elementId=element1',
        'http://localhost:8090/?url=test.drawio&elementId=shape1',
        'http://localhost:8090/?elementId=testelem&format=svg',
        'http://localhost:8090/?pageId=page1&elementId=element2'
    ];
    
    testUrls.forEach(function(url) {
        console.log('Testing URL:', url);
        var params = new URLSearchParams(url.split('?')[1] || '');
        var elementId = params.get('elementId');
        console.log('Extracted elementId:', elementId);
    });
}

// Usage examples
function showUsageExamples() {
    console.log('\n=== Usage Examples ===');
    
    console.log('1. Basic programmatic usage:');
    console.log('   jumpToElement(graph, "your-element-id");');
    
    console.log('\n2. URL parameter usage:');
    console.log('   http://your-domain.com/drawio/?elementId=element1');
    
    console.log('\n3. Combined with other parameters:');
    console.log('   http://your-domain.com/drawio/?url=diagram.drawio&elementId=shape123');
    
    console.log('\n4. With page selection:');
    console.log('   http://your-domain.com/drawio/?pageId=page2&elementId=connector1');
}

// Run all tests
if (typeof jumpToElement === 'function') {
    runTests();
} else {
    console.log('jumpToElement function not found. Make sure export.js is loaded.');
}

testUrlParameterParsing();
showUsageExamples();