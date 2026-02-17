/**
 * ParameterSidebar - Schema-driven parameter tuning panel
 * 
 * Features:
 * - Toggle button to show/hide sidebar
 * - Collapsible parameter groups
 * - Sliders for numeric params (float/int)
 * - Checkboxes for boolean params
 * - Apply & Refresh button
 * - Reset to Defaults button
 */

import { useState, useEffect, useCallback } from 'react';
import { getAlgorithmConfig, updateAlgorithmConfig, computeParameters } from '../api';

// Styles for the sidebar
const styles = {
  toggleButton: {
    position: 'fixed',
    right: '20px',
    top: '80px',
    zIndex: 1000,
    padding: '10px 16px',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.3)',
    zIndex: 1001
  },
  sidebar: {
    position: 'fixed',
    top: 0,
    right: 0,
    width: '380px',
    height: '100vh',
    backgroundColor: '#ffffff',
    boxShadow: '-4px 0 20px rgba(0,0,0,0.15)',
    zIndex: 1002,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  },
  header: {
    padding: '20px',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#f9fafb'
  },
  title: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#111827',
    margin: 0
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: '#6b7280',
    padding: '4px'
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '16px'
  },
  footer: {
    padding: '16px 20px',
    borderTop: '1px solid #e5e7eb',
    backgroundColor: '#f9fafb',
    display: 'flex',
    gap: '12px',
    flexDirection: 'column'
  },
  buttonRow: {
    display: 'flex',
    gap: '12px'
  },
  applyButton: {
    flex: 1,
    padding: '12px 16px',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500'
  },
  resetButton: {
    padding: '12px 16px',
    backgroundColor: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500'
  },
  exportButton: {
    padding: '12px 16px',
    backgroundColor: '#10b981',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500'
  },
  group: {
    marginBottom: '16px',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    overflow: 'hidden'
  },
  groupHeader: {
    padding: '12px 16px',
    backgroundColor: '#f9fafb',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    userSelect: 'none'
  },
  groupTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
    margin: 0
  },
  groupContent: {
    padding: '12px 16px',
    borderTop: '1px solid #e5e7eb'
  },
  param: {
    marginBottom: '16px'
  },
  paramLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px'
  },
  paramName: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151'
  },
  paramValue: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#3b82f6',
    fontFamily: 'monospace'
  },
  paramDescription: {
    fontSize: '11px',
    color: '#6b7280',
    marginBottom: '8px'
  },
  slider: {
    width: '100%',
    height: '6px',
    borderRadius: '3px',
    appearance: 'none',
    backgroundColor: '#e5e7eb',
    cursor: 'pointer'
  },
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer'
  },
  algorithmInfo: {
    padding: '12px 16px',
    backgroundColor: '#f0f9ff',
    borderRadius: '8px',
    marginBottom: '16px',
    fontSize: '13px',
    color: '#0369a1'
  },
  errorBox: {
    padding: '12px 16px',
    backgroundColor: '#fef2f2',
    borderRadius: '8px',
    marginBottom: '16px',
    fontSize: '13px',
    color: '#dc2626'
  },
  sectionDivider: {
    margin: '24px 0 16px',
    padding: '8px 12px',
    backgroundColor: '#f0f9ff',
    borderLeft: '3px solid #3b82f6',
    borderRadius: '4px'
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#0369a1',
    margin: 0,
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  readonlyParam: {
    opacity: 0.8,
    backgroundColor: '#f9fafb'
  },
  readonlyInput: {
    pointerEvents: 'none',
    opacity: 0.6
  },
  lockIcon: {
    fontSize: '12px',
    marginLeft: '6px',
    color: '#9ca3af'
  },
  loadingBox: {
    padding: '40px',
    textAlign: 'center',
    color: '#6b7280'
  },
  changeIndicator: {
    display: 'inline-block',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#f59e0b',
    marginLeft: '8px'
  }
};

// Helper to get nested value from config
function getNestedValue(obj, keyPath) {
  const parts = keyPath.split('.');
  let value = obj;
  for (const part of parts) {
    if (value && typeof value === 'object' && part in value) {
      value = value[part];
    } else {
      return undefined;
    }
  }
  return value;
}

// Helper to set nested value in config
function setNestedValue(obj, keyPath, value) {
  const parts = keyPath.split('.');
  const result = JSON.parse(JSON.stringify(obj)); // Deep clone
  let current = result;
  
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (!(part in current)) {
      current[part] = {};
    }
    current = current[part];
  }
  
  current[parts[parts.length - 1]] = value;
  return result;
}

export default function ParameterSidebar({ 
  isOpen, 
  onToggle, 
  onApplyAndRefresh,
  configLoaded 
}) {
  const [schema, setSchema] = useState(null);
  const [originalConfig, setOriginalConfig] = useState({});
  const [localConfig, setLocalConfig] = useState({});
  const [computedParams, setComputedParams] = useState({});
  const [algorithmInfo, setAlgorithmInfo] = useState(null);
  const [collapsedGroups, setCollapsedGroups] = useState({});
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Compute derived parameters
  const updateComputedParams = useCallback(async (baseParams) => {
    try {
      const result = await computeParameters(baseParams, null);
      setComputedParams(result.computed || {});
    } catch (err) {
      console.error('Failed to compute parameters:', err);
      // Don't set error state - this is non-critical
    }
  }, []);

  // Load config and schema
  const loadConfig = useCallback(async () => {
    if (!configLoaded) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await getAlgorithmConfig();
      setSchema(result.schema);
      setOriginalConfig(result.config);
      setLocalConfig(result.config);
      setAlgorithmInfo({
        name: result.algorithm_name,
        version: result.algorithm_version,
        folder: result.algorithm
      });
      
      // Set initial collapsed state from schema
      const collapsed = {};
      result.schema?.groups?.forEach(group => {
        collapsed[group.id] = group.collapsed || false;
      });
      setCollapsedGroups(collapsed);
      setHasChanges(false);
      
      // Compute initial derived parameters
      await updateComputedParams(result.config);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [configLoaded, updateComputedParams]);

  useEffect(() => {
    if (isOpen && configLoaded) {
      loadConfig();
    }
  }, [isOpen, configLoaded, loadConfig]);

  // Toggle group collapse
  const toggleGroup = (groupId) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [groupId]: !prev[groupId]
    }));
  };

  // Handle parameter change
  const handleParamChange = (keyPath, value, paramType) => {
    let parsedValue = value;
    
    if (paramType === 'int') {
      parsedValue = parseInt(value, 10);
      if (isNaN(parsedValue)) return;
    } else if (paramType === 'float') {
      parsedValue = parseFloat(value);
      if (isNaN(parsedValue)) return;
    } else if (paramType === 'boolean') {
      parsedValue = Boolean(value);
    }
    
    let newConfig = setNestedValue(localConfig, keyPath, parsedValue);
    
    // Handle sum_to_one constraints - auto-adjust other parameters proportionally
    if (schema?.constraints) {
      for (const constraint of schema.constraints) {
        if (constraint.type === 'sum_to_one' && constraint.params.includes(keyPath)) {
          const constraintParams = constraint.params;
          const changedParam = keyPath;
          const otherParams = constraintParams.filter(p => p !== changedParam);
          
          // Get current values
          const changedValue = parsedValue;
          const otherValues = otherParams.map(p => getNestedValue(newConfig, p) || 0);
          const otherSum = otherValues.reduce((sum, v) => sum + v, 0);
          
          // Calculate remaining weight to distribute
          const remaining = 1.0 - changedValue;
          
          if (remaining >= 0 && remaining <= 1.0) {
            // Proportionally adjust other parameters
            if (otherSum > 0) {
              otherParams.forEach((paramKey, idx) => {
                const proportion = otherValues[idx] / otherSum;
                const newValue = remaining * proportion;
                newConfig = setNestedValue(newConfig, paramKey, newValue);
              });
            } else {
              // If other params are zero, distribute equally
              const equalShare = remaining / otherParams.length;
              otherParams.forEach(paramKey => {
                newConfig = setNestedValue(newConfig, paramKey, equalShare);
              });
            }
          }
        }
      }
    }
    
    setLocalConfig(newConfig);
    setHasChanges(JSON.stringify(newConfig) !== JSON.stringify(originalConfig));
    
    // Update computed parameters in real-time
    updateComputedParams(newConfig);
  };

  // Apply changes
  const handleApply = async () => {
    setApplying(true);
    setError(null);
    
    try {
      const result = await updateAlgorithmConfig(localConfig);
      setOriginalConfig(result.config);
      setLocalConfig(result.config);
      setHasChanges(false);
      
      // Trigger For You refresh
      if (onApplyAndRefresh) {
        onApplyAndRefresh();
      }
      
      // Notify other components (e.g., Tests page) that config changed
      window.dispatchEvent(new CustomEvent('algorithm-config-changed'));
    } catch (err) {
      setError(err.message);
    } finally {
      setApplying(false);
    }
  };

  // Reset to original
  const handleReset = async () => {
    setLocalConfig(originalConfig);
    setError(null);
    
    // Recalculate computed parameters for the reset config
    updateComputedParams(originalConfig);
    
    // Apply reset to backend immediately
    setApplying(true);
    try {
      const result = await updateAlgorithmConfig(originalConfig);
      setOriginalConfig(result.config);
      setLocalConfig(result.config);
      setHasChanges(false);
      
      // Trigger For You refresh
      if (onApplyAndRefresh) {
        onApplyAndRefresh();
      }
      
      // Notify Tests page that config changed
      window.dispatchEvent(new CustomEvent('algorithm-config-changed'));
    } catch (err) {
      setError(err.message);
    } finally {
      setApplying(false);
    }
  };

  // Export config as JSON
  const handleExport = () => {
    const configToExport = {
      algorithm: algorithmInfo?.folder,
      algorithm_name: algorithmInfo?.name,
      algorithm_version: algorithmInfo?.version,
      base_params: localConfig,
      computed_params: computedParams,
      exported_at: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(configToExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${algorithmInfo?.folder || 'algorithm'}_config_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Render parameter input based on type
  const renderParamInput = (param, value, isReadonly = false) => {
    const defaultValue = param.default;
    const displayValue = value !== undefined ? value : defaultValue;
    
    if (param.type === 'boolean') {
      // Warn about boolean parameters in base params (not readonly)
      if (!isReadonly) {
        return (
          <div style={{color: '#dc2626', fontSize: '12px', padding: '8px', backgroundColor: '#fef2f2', borderRadius: '4px'}}>
            ⚠️ Boolean parameters are not recommended for tuning. This may cause runtime errors. Consider making this an algorithm-level constant.
          </div>
        );
      }
      
      // Readonly boolean (computed param) - render as disabled checkbox
      return (
        <input
          type="checkbox"
          checked={displayValue}
          onChange={(e) => !isReadonly && handleParamChange(param.key, e.target.checked, 'boolean')}
          style={{
            ...styles.checkbox,
            ...(isReadonly ? styles.readonlyInput : {})
          }}
          disabled={isReadonly}
        />
      );
    }
    
    // Numeric slider
    const min = param.min ?? 0;
    const max = param.max ?? 100;
    const step = param.step ?? (param.type === 'int' ? 1 : 0.01);
    
    return (
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={displayValue}
        onChange={(e) => !isReadonly && handleParamChange(param.key, e.target.value, param.type)}
        style={{
          ...styles.slider,
          ...(isReadonly ? styles.readonlyInput : {})
        }}
        disabled={isReadonly}
      />
    );
  };

  // Format value for display
  const formatValue = (value, paramType) => {
    if (value === undefined || value === null) return 'N/A';
    if (paramType === 'boolean') return value ? 'true' : 'false';
    if (paramType === 'float') return typeof value === 'number' ? value.toFixed(2) : String(value);
    if (paramType === 'int') return String(Math.round(value));
    if (paramType === 'string') return String(value);
    return String(value);
  };

  // Toggle button (always visible)
  const toggleButton = (
    <button
      onClick={onToggle}
      style={{
        ...styles.toggleButton,
        backgroundColor: hasChanges ? '#f59e0b' : '#3b82f6'
      }}
    >
      <span>Tune Parameters</span>
      {hasChanges && <span style={styles.changeIndicator} />}
    </button>
  );

  if (!isOpen) {
    return configLoaded ? toggleButton : null;
  }

  return (
    <>
      {toggleButton}
      <div style={styles.overlay} onClick={onToggle} />
      <div style={styles.sidebar}>
        {/* Header */}
        <div style={styles.header}>
          <h2 style={styles.title}>Parameter Tuning</h2>
          <button style={styles.closeButton} onClick={onToggle}>×</button>
        </div>
        
        {/* Content */}
        <div style={styles.content}>
          {loading && (
            <div style={styles.loadingBox}>Loading configuration...</div>
          )}
          
          {error && (
            <div style={styles.errorBox}>{error}</div>
          )}
          
          {!loading && algorithmInfo && (
            <div style={styles.algorithmInfo}>
              <strong>{algorithmInfo.name}</strong> (v{algorithmInfo.version})
              <br />
              <span style={{ fontSize: '11px', opacity: 0.8 }}>{algorithmInfo.folder}</span>
            </div>
          )}
          
          {!loading && schema?.groups && (
            <>
              {/* Base Parameters Section */}
              {schema.groups.filter(g => g.section !== 'computed').length > 0 && (
                <>
                  <div style={styles.sectionDivider}>
                    <h4 style={styles.sectionTitle}>Base Parameters (Editable)</h4>
                  </div>
                  {schema.groups
                    .filter(g => g.section !== 'computed')
                    .map(group => (
                      <div key={group.id} style={styles.group}>
                        <div 
                          style={styles.groupHeader}
                          onClick={() => toggleGroup(group.id)}
                        >
                          <h3 style={styles.groupTitle}>{group.label}</h3>
                          <span>{collapsedGroups[group.id] ? '▸' : '▾'}</span>
                        </div>
                        
                        {!collapsedGroups[group.id] && (
                          <div style={styles.groupContent}>
                            {group.params?.map(param => {
                              const value = getNestedValue(localConfig, param.key);
                              const displayValue = formatValue(value, param.type);
                              
                              return (
                                <div key={param.key} style={styles.param}>
                                  <div style={styles.paramLabel}>
                                    <span style={styles.paramName}>{param.label}</span>
                                    <span style={styles.paramValue}>{displayValue}</span>
                                  </div>
                                  {param.description && (
                                    <div style={styles.paramDescription}>{param.description}</div>
                                  )}
                                  {renderParamInput(param, value, false)}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                </>
              )}
              
              {/* Computed Parameters Section */}
              {schema.groups.filter(g => g.section === 'computed').length > 0 && (
                <>
                  <div style={styles.sectionDivider}>
                    <h4 style={styles.sectionTitle}>Computed Parameters (Read-only)</h4>
                  </div>
                  {schema.groups
                    .filter(g => g.section === 'computed')
                    .map(group => (
                      <div key={group.id} style={styles.group}>
                        <div 
                          style={styles.groupHeader}
                          onClick={() => toggleGroup(group.id)}
                        >
                          <h3 style={styles.groupTitle}>{group.label}</h3>
                          <span>{collapsedGroups[group.id] ? '▸' : '▾'}</span>
                        </div>
                        
                        {!collapsedGroups[group.id] && (
                          <div style={styles.groupContent}>
                            {group.params?.map(param => {
                              const value = computedParams[param.key];
                              const displayValue = formatValue(value, param.type);
                              
                              return (
                                <div key={param.key} style={{...styles.param, ...styles.readonlyParam}}>
                                  <div style={styles.paramLabel}>
                                    <span style={styles.paramName}>
                                      {param.label}
                                      <span style={styles.lockIcon}>🔒</span>
                                    </span>
                                    <span style={styles.paramValue}>{displayValue}</span>
                                  </div>
                                  {param.description && (
                                    <div style={styles.paramDescription}>{param.description}</div>
                                  )}
                                  {renderParamInput(param, value, true)}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                </>
              )}
            </>
          )}
        </div>
        
        {/* Footer */}
        <div style={styles.footer}>
          {hasChanges && (
            <div style={{ fontSize: '12px', color: '#f59e0b', textAlign: 'center' }}>
              You have unsaved changes
            </div>
          )}
          <div style={styles.buttonRow}>
            <button 
              style={styles.resetButton}
              onClick={handleReset}
              disabled={!hasChanges || applying}
            >
              Reset
            </button>
            <button 
              style={styles.exportButton}
              onClick={handleExport}
              disabled={applying}
              title="Export current configuration as JSON"
            >
              Export
            </button>
            <button 
              style={{
                ...styles.applyButton,
                opacity: (!hasChanges || applying) ? 0.6 : 1,
                cursor: (!hasChanges || applying) ? 'not-allowed' : 'pointer'
              }}
              onClick={handleApply}
              disabled={!hasChanges || applying}
            >
              {applying ? 'Applying...' : 'Apply & Refresh'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
