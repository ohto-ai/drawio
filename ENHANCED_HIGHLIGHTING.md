# Enhanced Highlighting Functionality - StripedOverlayManager

This document describes the enhanced highlighting functionality added to the StripedOverlayManager class in `src/main/webapp/js/mod.js`.

## Overview

The enhanced StripedOverlayManager now supports two distinct types of highlights with a sophisticated priority system:

1. **Conditional Highlights** - Callback-based highlighting that evaluates each cell
2. **Specific Highlights** - Direct cell-list-based highlighting

## Key Features

- **Multiple Highlight Groups**: Support for multiple conditional and specific highlight groups simultaneously
- **Priority System**: Specific highlights override conditional highlights; later highlights override earlier ones
- **Individual Color Groups**: Each highlight group can have its own color cycling sequence
- **Backward Compatibility**: All existing APIs continue to work unchanged
- **Short-Circuit Evaluation**: Conditional highlights are evaluated from back to front for optimal performance

## API Reference

### New Methods

#### Conditional Highlights

```javascript
// Add a conditional highlight
manager.addConditionalHighlight(id, callback, colors)
// Parameters:
// - id (string): Unique identifier for this highlight group
// - callback (function): Function that takes a cell and returns true/false
// - colors (array): Array of color strings for cycling
// Returns: boolean (success/failure)

// Remove a conditional highlight
manager.removeConditionalHighlight(id)
// Parameters:
// - id (string): Identifier of the highlight group to remove
// Returns: boolean (success/failure)
```

#### Specific Highlights

```javascript
// Add a specific highlight
manager.addSpecificHighlight(id, cells, colors)
// Parameters:
// - id (string): Unique identifier for this highlight group
// - cells (array): Array of cell objects to highlight
// - colors (array): Array of color strings for cycling
// Returns: boolean (success/failure)

// Remove a specific highlight
manager.removeSpecificHighlight(id)
// Parameters:
// - id (string): Identifier of the highlight group to remove
// Returns: boolean (success/failure)
```

#### Information and Control

```javascript
// Get information about all conditional highlights
manager.getConditionalHighlights()
// Returns: Array of {id, colors, colorIndex} objects

// Get information about all specific highlights
manager.getSpecificHighlights()
// Returns: Array of {id, cells, colors, colorIndex} objects

// Manually refresh all highlights
manager.refresh()
// Forces re-evaluation and re-application of all highlights
```

### Priority System

The priority system works as follows:

1. **Specific highlights always take precedence over conditional highlights**
2. **Within the same type, later-added highlights take precedence over earlier ones**
3. **Conditional highlights are evaluated from back to front** (short-circuit evaluation)

Example:
```javascript
// Lower priority
manager.addConditionalHighlight('basic_alarm', callbackAlarm, ['#ff0000']);

// Higher priority (same cell, conditional)
manager.addConditionalHighlight('critical_alarm', callbackCritical, ['#800000']);

// Highest priority (same cell, specific)
manager.addSpecificHighlight('override', [someCell], ['#0000ff']);
```

## Usage Examples

### Basic Conditional Highlighting

```javascript
// Highlight cells with alarm=1 attribute
manager.addConditionalHighlight('alarms', 
    (cell) => {
        if (!cell || !cell.value) return false;
        return cell.value.getAttribute && 
               cell.value.getAttribute('alarm') === '1';
    }, 
    ['#ff0000', '#ff4444', '#ff8888'] // Red gradient cycling
);
```

### Basic Specific Highlighting

```javascript
// Get some cells
const importantCells = [cell1, cell2, cell3];

// Highlight specific cells
manager.addSpecificHighlight('important', 
    importantCells, 
    ['#00ff00', '#44ff44'] // Green gradient cycling
);
```

### Complex Priority Example

```javascript
const manager = window.ohtoai.stripedOverlayManager;

// 1. Base conditional highlight for all warnings
manager.addConditionalHighlight('warnings', 
    (cell) => cell.value?.getAttribute('status') === 'warning',
    ['#ffaa00'] // Orange
);

// 2. Higher priority conditional for errors
manager.addConditionalHighlight('errors', 
    (cell) => cell.value?.getAttribute('status') === 'error',
    ['#ff0000'] // Red - overrides warnings for error cells
);

// 3. Highest priority specific highlight
manager.addSpecificHighlight('critical_override', 
    [specificCriticalCell], 
    ['#800080'] // Purple - overrides everything for this cell
);

// Apply all highlights
manager.refresh();
```

### Working with Dynamic Data

```javascript
// Function to update highlights based on current data
function updateHighlightsFromData(data) {
    const manager = window.ohtoai.stripedOverlayManager;
    
    // Clear existing highlights
    manager.removeConditionalHighlight('data_based');
    manager.removeSpecificHighlight('critical_items');
    
    // Add conditional highlight based on data
    manager.addConditionalHighlight('data_based', 
        (cell) => {
            const id = cell.id;
            return data.highlightCells && data.highlightCells.includes(id);
        },
        data.colors || ['#ff0000', '#ffff00']
    );
    
    // Add specific highlights for critical items
    if (data.criticalCells && data.criticalCells.length > 0) {
        manager.addSpecificHighlight('critical_items',
            data.criticalCells,
            ['#ff0000', '#800000'] // Dark red
        );
    }
    
    // Apply changes
    manager.refresh();
}
```

## Backward Compatibility

All existing methods continue to work exactly as before:

```javascript
// Existing API remains unchanged
manager.startAutoHighlight(callback);
manager.stopAutoHighlight();
manager.setHighlightColors(['#ff0000', '#ffff00']);
manager.applyHighlight(cells);
manager.clearHighlight();
manager.updateHighlight(callback);
```

The `startAutoHighlight()` method now internally uses the new system but maintains the same external behavior.

## Performance Considerations

- **Short-circuit evaluation**: Conditional highlights are evaluated from back to front, stopping at the first match
- **Efficient cell tracking**: Each cell tracks its highlight source to avoid unnecessary re-evaluation
- **Optimized color cycling**: Colors are cycled per-highlight-group rather than globally

## Migration Guide

### From Single Callback to Multiple Conditional Highlights

**Before:**
```javascript
manager.startAutoHighlight((cell) => {
    return cell.value?.getAttribute('alarm') === '1';
});
```

**After (recommended):**
```javascript
manager.addConditionalHighlight('alarm_highlight',
    (cell) => cell.value?.getAttribute('alarm') === '1',
    ['#ff0000', '#ffff00']
);
manager.refresh();
```

### From Manual Cell Highlighting to Specific Highlights

**Before:**
```javascript
manager.applyHighlight([cell1, cell2, cell3]);
```

**After (recommended):**
```javascript
manager.addSpecificHighlight('manual_selection',
    [cell1, cell2, cell3],
    ['#ff0000', '#ffff00']
);
manager.refresh();
```

## Error Handling

The enhanced system includes robust error handling:

- Invalid callback functions in conditional highlights are caught and logged
- Malformed parameters return false from API methods
- Missing or null cells are safely handled
- Color array validation ensures at least one color is provided

## Testing

A test script is available at `test_highlight_enhancement.js` that demonstrates all features:

```javascript
// Run in browser console when draw.io is loaded
testHighlightEnhancements();
```

## Debugging

To debug highlighting issues:

```javascript
const manager = window.ohtoai.stripedOverlayManager;

// Check current highlight definitions
console.log('Conditional:', manager.getConditionalHighlights());
console.log('Specific:', manager.getSpecificHighlights());

// Check which cells are currently highlighted
console.log('Highlighted cells:', Array.from(manager.cellsWithHighlight));

// Manually refresh to see evaluation
manager.refresh();
```