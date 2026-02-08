/**
 * Tests Page - Run and view evaluation test results
 * 
 * Features:
 * - List all test cases
 * - Run individual tests
 * - Run all tests
 * - View results with criteria breakdown
 * - View historical reports
 */

import { useState, useEffect } from 'react';
import { 
  listTestCases, 
  runTest, 
  runAllTests, 
  listReports,
  getReport,
  getConfigStatus 
} from '../api';

export default function TestsPage({ geminiKey }) {
  const [testCases, setTestCases] = useState([]);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(null); // null, 'all', or test_id
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [configStatus, setConfigStatus] = useState(null);
  const [view, setView] = useState('tests'); // 'tests' or 'reports'
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [testsRes, reportsRes, configRes] = await Promise.all([
        listTestCases().catch(() => ({ test_cases: [] })),
        listReports().catch(() => ({ reports: [] })),
        getConfigStatus().catch(() => ({ loaded: false }))
      ]);
      
      setTestCases(testsRes.test_cases || []);
      setReports(reportsRes.reports || []);
      setConfigStatus(configRes);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRunTest = async (testId) => {
    if (!configStatus?.loaded) {
      setError('No algorithm/dataset loaded. Load a configuration first.');
      return;
    }
    
    setRunning(testId);
    setError(null);
    
    try {
      // Check if test supports LLM evaluation
      const testCase = testCases.find(t => t.id === testId);
      const supportsLlm = testCase?.evaluation_method?.includes('llm');
      const enableLlm = supportsLlm && !!geminiKey;
      
      const result = await runTest(testId, { 
        geminiKey,
        withLlm: enableLlm 
      });
      setResults(prev => ({ ...prev, [testId]: result }));
    } catch (err) {
      setError(`Test ${testId} failed: ${err.message}`);
    } finally {
      setRunning(null);
    }
  };

  const handleRunAll = async () => {
    if (!configStatus?.loaded) {
      setError('No algorithm/dataset loaded. Load a configuration first.');
      return;
    }
    
    setRunning('all');
    setError(null);
    setResults({});
    
    try {
      // Enable LLM evaluation if Gemini key is provided
      const enableLlm = !!geminiKey;
      
      const report = await runAllTests({ 
        geminiKey,
        withLlm: enableLlm,
        saveReport: true
      });
      
      // Populate results from report
      const newResults = {};
      for (const r of report.results || []) {
        newResults[r.test_id] = r;
      }
      setResults(newResults);
      
      // Refresh reports list
      const reportsRes = await listReports();
      setReports(reportsRes.reports || []);
    } catch (err) {
      setError(`Run all tests failed: ${err.message}`);
    } finally {
      setRunning(null);
    }
  };

  const handleViewReport = async (reportId) => {
    try {
      const report = await getReport(reportId);
      setSelectedReport(report);
    } catch (err) {
      setError(`Failed to load report: ${err.message}`);
    }
  };

  const passedCount = Object.values(results).filter(r => r.passed).length;
  const failedCount = Object.values(results).filter(r => !r.passed).length;
  const totalRun = passedCount + failedCount;

  if (loading) {
    return (
      <div className="p-4 text-slate-400">
        Loading test cases...
      </div>
    );
  }

  return (
    <div className="p-4 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Evaluation Tests</h1>
          <p className="text-slate-400 text-sm">
            {configStatus?.loaded 
              ? `Running on ${configStatus.algorithm_folder} / ${configStatus.dataset_folder}`
              : 'No configuration loaded'
            }
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setView(view === 'tests' ? 'reports' : 'tests')}
            className="px-4 py-2 bg-slate-700 text-slate-300 text-sm font-medium rounded-lg hover:bg-slate-600"
          >
            {view === 'tests' ? 'View Reports' : 'Run Tests'}
          </button>
          {view === 'tests' && (
            <button
              onClick={handleRunAll}
              disabled={running !== null || !configStatus?.loaded}
              className={`px-4 py-2 text-sm font-medium rounded-lg ${
                running !== null || !configStatus?.loaded
                  ? 'bg-green-600/30 text-green-400/50 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-500'
              }`}
            >
              {running === 'all' ? 'Running All...' : 'Run All Tests'}
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
          <button 
            onClick={() => setError(null)} 
            className="ml-2 text-red-300 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Config Warning */}
      {!configStatus?.loaded && (
        <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm">
          No algorithm/dataset loaded. Go to Settings to load a configuration before running tests.
        </div>
      )}

      {view === 'tests' ? (
        <>
          {/* Results Summary with Overall Score */}
          {totalRun > 0 && (
            <div className="mb-6">
              <div className="grid grid-cols-4 gap-4">
                <StatCard 
                  label="Total Run" 
                  value={totalRun} 
                  color="blue" 
                />
                <StatCard 
                  label="Passed" 
                  value={passedCount} 
                  color="green" 
                />
                <StatCard 
                  label="Failed" 
                  value={failedCount} 
                  color="red" 
                />
                <OverallScoreCard results={results} />
              </div>
            </div>
          )}

          {/* Test Cases List */}
          <div className="space-y-4">
            {testCases.map(test => (
              <TestCard
                key={test.id}
                test={test}
                result={results[test.id]}
                running={running === test.id}
                disabled={running !== null || !configStatus?.loaded}
                onRun={() => handleRunTest(test.id)}
              />
            ))}
            
            {testCases.length === 0 && (
              <div className="text-center text-slate-500 py-8">
                No test cases found. Check the evaluation/test_cases directory.
              </div>
            )}
          </div>
        </>
      ) : (
        /* Reports View */
        <div>
          {selectedReport ? (
            <ReportDetail 
              report={selectedReport} 
              onBack={() => setSelectedReport(null)} 
            />
          ) : (
            <div className="space-y-3">
              {reports.map(report => (
                <div 
                  key={report.id}
                  onClick={() => handleViewReport(report.id)}
                  className="bg-slate-800 border border-slate-700 rounded-lg p-4 cursor-pointer hover:border-slate-600"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white font-medium">{report.id}</p>
                      <p className="text-slate-400 text-sm">
                        {new Date(report.timestamp).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-green-400">
                        {report.passed} passed
                      </span>
                      <span className="text-red-400">
                        {report.failed} failed
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              
              {reports.length === 0 && (
                <div className="text-center text-slate-500 py-8">
                  No reports yet. Run tests to generate a report.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TestCard({ test, result, running, disabled, onRun }) {
  const [expanded, setExpanded] = useState(false);
  
  const getStatusColor = () => {
    if (!result) return 'border-slate-700';
    return result.passed ? 'border-green-500/50' : 'border-red-500/50';
  };
  
  const getStatusBadge = () => {
    if (running) return <span className="text-xs px-2 py-1 bg-blue-500/20 text-blue-400 rounded">Running...</span>;
    if (!result) return <span className="text-xs px-2 py-1 bg-slate-600 text-slate-300 rounded">Not Run</span>;
    if (result.passed) return <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded">Passed</span>;
    return <span className="text-xs px-2 py-1 bg-red-500/20 text-red-400 rounded">Failed</span>;
  };
  
  // Get aggregate score for display
  const aggregateScore = result?.scores?.aggregate_score;

  return (
    <div className={`bg-slate-800 border rounded-lg overflow-hidden ${getStatusColor()}`}>
      <div className="p-4 flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <span className="font-mono text-sm text-slate-400">{test.id}</span>
            {getStatusBadge()}
            {aggregateScore !== undefined && (
              <ScoreBadge score={aggregateScore} />
            )}
            <span className={`text-xs px-2 py-0.5 rounded ${
              test.evaluation_method === 'deterministic' 
                ? 'bg-blue-500/20 text-blue-400'
                : test.evaluation_method === 'llm'
                ? 'bg-purple-500/20 text-purple-400'
                : 'bg-indigo-500/20 text-indigo-400'
            }`}>
              {test.evaluation_method}
            </span>
          </div>
          <h3 className="text-white font-medium">{test.name}</h3>
          <p className="text-slate-400 text-sm mt-1">{test.description}</p>
        </div>
        
        <div className="flex items-center gap-2 ml-4">
          {result && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
            >
              {expanded ? 'Hide' : 'Details'}
            </button>
          )}
          <button
            onClick={onRun}
            disabled={disabled || running}
            className={`px-4 py-2 text-sm font-medium rounded-lg ${
              disabled || running
                ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-500'
            }`}
          >
            {running ? '...' : 'Run'}
          </button>
        </div>
      </div>
      
      {/* Expanded Details with Scalar Scores */}
      {expanded && result && (
        <div className="border-t border-slate-700 p-4 bg-slate-850">
          {result.error && (
            <div className="mb-3 p-2 bg-red-500/10 border border-red-500/30 rounded text-red-400 text-sm">
              Error: {result.error}
            </div>
          )}
          
          {/* Aggregate Score Summary */}
          {result.scores && (
            <div className="mb-4 p-3 bg-slate-700/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-300 font-medium">Test Aggregate Score</span>
                <span className={`text-lg font-bold ${getScoreColor(result.scores.aggregate_score)}`}>
                  {result.scores.aggregate_score?.toFixed(1)}/10
                </span>
              </div>
              <ScoreProgressBar 
                score={result.scores.aggregate_score} 
                threshold={7.0}
                showThreshold={true}
              />
              <div className="mt-2 flex justify-between text-xs text-slate-500">
                <span>{result.scores.passed_count}/{result.scores.criteria_count} criteria passed</span>
                <span>Confidence: {(result.scores.aggregate_confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
          
          <h4 className="text-sm font-medium text-slate-300 mb-2">Criteria Results</h4>
          <div className="space-y-3">
            {result.criteria_results?.map((cr, idx) => (
              <CriterionCard key={idx} criterion={cr} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CriterionCard({ criterion: cr }) {
  const hasScalarScore = cr.score !== undefined;
  
  return (
    <div 
      className={`p-3 rounded-lg text-sm ${
        cr.passed 
          ? 'bg-green-500/10 border border-green-500/20' 
          : 'bg-red-500/10 border border-red-500/20'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={cr.passed ? 'text-green-400' : 'text-red-400'}>
            {cr.passed ? '✓' : '✗'}
          </span>
          <span className="text-white font-mono text-xs">{cr.criterion_id}</span>
          {cr.weight && cr.weight !== 1.0 && (
            <span className="text-xs text-slate-500">({cr.weight}x weight)</span>
          )}
        </div>
        {hasScalarScore && (
          <div className="flex items-center gap-2">
            <span className={`font-bold ${getScoreColor(cr.score)}`}>
              {cr.score?.toFixed(1)}/10
            </span>
            <span className="text-slate-500 text-xs">(min: {cr.threshold})</span>
          </div>
        )}
      </div>
      
      <p className="text-slate-300 mb-2">{cr.description}</p>
      
      {/* Score Progress Bar */}
      {hasScalarScore && (
        <ScoreProgressBar 
          score={cr.score} 
          threshold={cr.threshold}
          showThreshold={true}
          compact={true}
        />
      )}
      
      {cr.details && (
        <p className="text-slate-500 text-xs mt-2 font-mono">{cr.details}</p>
      )}
      
      {/* Confidence indicator for non-deterministic */}
      {cr.confidence !== undefined && cr.confidence < 1.0 && (
        <div className="mt-2 flex items-center gap-1 text-xs text-slate-500">
          <span>Confidence:</span>
          <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-purple-500 rounded-full"
              style={{ width: `${cr.confidence * 100}%` }}
            />
          </div>
          <span>{(cr.confidence * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}

function ScoreProgressBar({ score, threshold = 7.0, showThreshold = false, compact = false }) {
  const percentage = Math.min(100, Math.max(0, (score / 10) * 100));
  const thresholdPercentage = (threshold / 10) * 100;
  
  return (
    <div className={`relative ${compact ? 'h-2' : 'h-3'} bg-slate-700 rounded-full overflow-hidden`}>
      {/* Score bar */}
      <div 
        className={`h-full rounded-full transition-all duration-300 ${
          score >= threshold 
            ? 'bg-gradient-to-r from-green-600 to-green-400' 
            : score >= threshold - 1.5 
            ? 'bg-gradient-to-r from-yellow-600 to-yellow-400'
            : 'bg-gradient-to-r from-red-600 to-red-400'
        }`}
        style={{ width: `${percentage}%` }}
      />
      {/* Threshold marker */}
      {showThreshold && (
        <div 
          className="absolute top-0 bottom-0 w-0.5 bg-white/50"
          style={{ left: `${thresholdPercentage}%` }}
        />
      )}
    </div>
  );
}

function ScoreBadge({ score }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
      score >= 8 
        ? 'bg-green-500/20 text-green-400' 
        : score >= 6 
        ? 'bg-yellow-500/20 text-yellow-400'
        : 'bg-red-500/20 text-red-400'
    }`}>
      {score?.toFixed(1)}/10
    </span>
  );
}

function getScoreColor(score) {
  if (score >= 8) return 'text-green-400';
  if (score >= 6) return 'text-yellow-400';
  return 'text-red-400';
}

function OverallScoreCard({ results }) {
  // Calculate overall score from all results
  const resultsArray = Object.values(results);
  if (resultsArray.length === 0) return null;
  
  let totalWeight = 0;
  let weightedScore = 0;
  const mftTests = ['03_quality_gates_credibility', '04_excluded_episodes'];
  
  for (const r of resultsArray) {
    if (r?.scores?.aggregate_score !== undefined) {
      const weight = mftTests.includes(r.test_id) ? 2.0 : 1.0;
      weightedScore += r.scores.aggregate_score * weight;
      totalWeight += weight;
    }
  }
  
  const overallScore = totalWeight > 0 ? weightedScore / totalWeight : 0;
  
  return (
    <div className={`rounded-xl p-4 border ${
      overallScore >= 8 
        ? 'bg-green-500/10 border-green-500/30' 
        : overallScore >= 6 
        ? 'bg-yellow-500/10 border-yellow-500/30'
        : 'bg-red-500/10 border-red-500/30'
    }`}>
      <div className="text-xs text-slate-400 mb-1">Overall Score</div>
      <div className={`text-2xl font-bold ${getScoreColor(overallScore)}`}>
        {overallScore.toFixed(1)}/10
      </div>
      <ScoreProgressBar score={overallScore} threshold={7.0} compact={true} />
    </div>
  );
}

function ReportDetail({ report, onBack }) {
  const overallScore = report.summary?.overall_score;
  
  return (
    <div>
      <button
        onClick={onBack}
        className="mb-4 text-slate-400 hover:text-white flex items-center gap-2"
      >
        ← Back to Reports
      </button>
      
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-4">
        <h2 className="text-xl font-bold text-white mb-2">Test Report</h2>
        <p className="text-slate-400 text-sm">
          {new Date(report.timestamp).toLocaleString()}
        </p>
        
        <div className="grid grid-cols-4 gap-4 mt-4">
          <div className="text-center p-3 bg-slate-700/50 rounded">
            <div className="text-2xl font-bold text-white">{report.summary?.total_tests || 0}</div>
            <div className="text-xs text-slate-400">Total</div>
          </div>
          <div className="text-center p-3 bg-green-500/10 rounded">
            <div className="text-2xl font-bold text-green-400">{report.summary?.passed || 0}</div>
            <div className="text-xs text-slate-400">Passed</div>
          </div>
          <div className="text-center p-3 bg-red-500/10 rounded">
            <div className="text-2xl font-bold text-red-400">{report.summary?.failed || 0}</div>
            <div className="text-xs text-slate-400">Failed</div>
          </div>
          {overallScore !== undefined && (
            <div className={`text-center p-3 rounded ${
              overallScore >= 8 
                ? 'bg-green-500/10' 
                : overallScore >= 6 
                ? 'bg-yellow-500/10'
                : 'bg-red-500/10'
            }`}>
              <div className={`text-2xl font-bold ${getScoreColor(overallScore)}`}>
                {overallScore?.toFixed(1)}
              </div>
              <div className="text-xs text-slate-400">Overall Score</div>
            </div>
          )}
        </div>
        
        {/* Score Breakdown */}
        {report.summary?.score_breakdown && (
          <div className="mt-4 pt-4 border-t border-slate-700">
            <div className="text-xs text-slate-400 mb-2">Score Breakdown by Test</div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(report.summary.score_breakdown).map(([testId, score]) => (
                <span 
                  key={testId}
                  className={`text-xs px-2 py-1 rounded font-mono ${
                    score >= 8 
                      ? 'bg-green-500/20 text-green-400' 
                      : score >= 6 
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}
                >
                  {testId.split('_')[0]}: {score?.toFixed(1)}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {report.context && (
          <div className="mt-4 pt-4 border-t border-slate-700">
            <p className="text-xs text-slate-500">
              Algorithm: {report.context.algorithm_name} ({report.context.algorithm_version}) |
              Dataset: {report.context.dataset_version} ({report.context.dataset_episode_count} episodes)
            </p>
          </div>
        )}
      </div>
      
      <div className="space-y-3">
        {(report.results || []).map((result, idx) => (
          <div 
            key={idx}
            className={`bg-slate-800 border rounded-lg p-4 ${
              result.passed ? 'border-green-500/30' : 'border-red-500/30'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className={result.passed ? 'text-green-400' : 'text-red-400'}>
                  {result.passed ? '✓' : '✗'}
                </span>
                <span className="text-white font-medium">{result.name}</span>
                <span className="text-xs text-slate-500 font-mono">{result.test_id}</span>
              </div>
              {result.scores?.aggregate_score !== undefined && (
                <ScoreBadge score={result.scores.aggregate_score} />
              )}
            </div>
            
            {/* Test aggregate score bar */}
            {result.scores?.aggregate_score !== undefined && (
              <div className="mb-3">
                <ScoreProgressBar 
                  score={result.scores.aggregate_score} 
                  threshold={7.0}
                  showThreshold={true}
                  compact={true}
                />
              </div>
            )}
            
            {result.error && (
              <p className="text-red-400 text-sm mb-2">Error: {result.error}</p>
            )}
            
            <div className="flex flex-wrap gap-2">
              {result.criteria_results?.map((cr, cIdx) => (
                <span 
                  key={cIdx}
                  className={`text-xs px-2 py-1 rounded ${
                    cr.passed 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-red-500/20 text-red-400'
                  }`}
                  title={`${cr.details} | Score: ${cr.score?.toFixed(1)}/${cr.threshold}`}
                >
                  {cr.criterion_id}: {cr.score !== undefined ? `${cr.score?.toFixed(1)}` : (cr.passed ? '✓' : '✗')}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    red: 'bg-red-500/10 border-red-500/30 text-red-400',
  };
  
  return (
    <div className={`rounded-xl p-4 border ${colorClasses[color] || colorClasses.blue}`}>
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
