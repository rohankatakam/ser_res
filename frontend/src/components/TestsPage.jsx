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
  getConfigStatus,
  getJudgeConfig,
  getTestCase
} from '../api';

export default function TestsPage() {
  const [testCases, setTestCases] = useState([]);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(null); // null, 'all', or test_id
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [configStatus, setConfigStatus] = useState(null);
  const [view, setView] = useState('tests'); // 'tests' or 'reports'
  const [error, setError] = useState(null);
  const [judgeConfig, setJudgeConfig] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [testsRes, reportsRes, configRes, judgeRes] = await Promise.all([
        listTestCases().catch(() => ({ test_cases: [] })),
        listReports().catch(() => ({ reports: [] })),
        getConfigStatus().catch(() => ({ loaded: false })),
        getJudgeConfig().catch(() => null)
      ]);

      setTestCases(testsRes.test_cases || []);
      setReports(reportsRes.reports || []);
      setConfigStatus(configRes);
      setJudgeConfig(judgeRes);
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
      // LLM evaluation always runs (multi-LLM via judges package)
      const result = await runTest(testId);
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
      // LLM evaluation always runs (multi-LLM via judges package)
      const report = await runAllTests({
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
          {judgeConfig && (
            <p className="text-slate-500 text-xs mt-1">
              LLM Judges: {judgeConfig.judges
                .filter(j => j.enabled)
                .map(j => j.provider)
                .join(', ') || 'None'}
              {judgeConfig.default_n > 1 && ` (N=${judgeConfig.default_n})`}
            </p>
          )}
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
              className={`px-4 py-2 text-sm font-medium rounded-lg ${running !== null || !configStatus?.loaded
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
          No algorithm/dataset loaded. The backend may still be starting up — try refreshing.
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
  const [activeTab, setActiveTab] = useState('results'); // 'results' or 'definition'
  const [definition, setDefinition] = useState(null);
  const [loadingDefinition, setLoadingDefinition] = useState(false);

  // Load definition when Definition tab is clicked
  const handleTabChange = async (tab) => {
    setActiveTab(tab);
    if (tab === 'definition' && !definition) {
      setLoadingDefinition(true);
      try {
        const def = await getTestCase(test.id);
        setDefinition(def);
      } catch (err) {
        console.error('Failed to load test definition:', err);
      } finally {
        setLoadingDefinition(false);
      }
    }
  };

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
            <span className={`text-xs px-2 py-0.5 rounded ${test.evaluation_method === 'deterministic'
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
            className={`px-4 py-2 text-sm font-medium rounded-lg ${disabled || running
              ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
              : 'bg-indigo-600 text-white hover:bg-indigo-500'
              }`}
          >
            {running ? '...' : 'Run'}
          </button>
        </div>
      </div>

      {/* Expanded Details with Tabs */}
      {expanded && (
        <div className="border-t border-slate-700 bg-slate-850">
          {/* Tab Bar */}
          <div className="flex border-b border-slate-700">
            <button
              onClick={() => handleTabChange('results')}
              className={`px-4 py-2 text-sm font-medium ${activeTab === 'results'
                ? 'text-indigo-400 border-b-2 border-indigo-400'
                : 'text-slate-400 hover:text-white'
                }`}
            >
              Results
            </button>
            <button
              onClick={() => handleTabChange('definition')}
              className={`px-4 py-2 text-sm font-medium ${activeTab === 'definition'
                ? 'text-indigo-400 border-b-2 border-indigo-400'
                : 'text-slate-400 hover:text-white'
                }`}
            >
              Definition
            </button>
          </div>

          <div className="p-4">
            {activeTab === 'results' && result && (
              <>
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

                {/* LLM Evaluation Section */}
                {result.llm_evaluation && (
                  <LlmEvaluationCard evaluation={result.llm_evaluation} />
                )}
              </>
            )}

            {activeTab === 'results' && !result && (
              <div className="text-center text-slate-500 py-8">
                No results yet. Run the test to see results.
              </div>
            )}

            {activeTab === 'definition' && (
              <TestDefinitionView
                definition={definition}
                loading={loadingDefinition}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TestDefinitionView({ definition, loading }) {
  if (loading) {
    return <div className="text-center text-slate-500 py-4">Loading definition...</div>;
  }

  if (!definition) {
    return <div className="text-center text-slate-500 py-4">Failed to load definition</div>;
  }

  return (
    <div className="space-y-4">
      {/* Metadata Section */}
      <div className="p-3 bg-slate-700/30 rounded-lg">
        <h4 className="text-sm font-medium text-slate-300 mb-2">Test Metadata</h4>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-slate-500">Type:</span>
            <span className={`ml-2 px-2 py-0.5 rounded text-xs ${definition.type === 'MFT'
              ? 'bg-blue-500/20 text-blue-400'
              : 'bg-purple-500/20 text-purple-400'
              }`}>
              {definition.type}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Method:</span>
            <span className="ml-2 text-slate-300">{definition.evaluation_method}</span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-500">Profiles:</span>
            <span className="ml-2">
              {definition.profiles?.map((p, i) => (
                <span key={p} className="inline-block px-2 py-0.5 bg-slate-600 text-slate-300 rounded text-xs mr-1">
                  {p}
                </span>
              ))}
            </span>
          </div>
        </div>
      </div>

      {/* Pass Criteria Table */}
      {definition.pass_criteria && definition.pass_criteria.length > 0 && (
        <div className="p-3 bg-slate-700/30 rounded-lg">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Pass Criteria</h4>
          <div className="space-y-2">
            {definition.pass_criteria.map((crit, idx) => (
              <div key={idx} className="p-2 bg-slate-800 rounded text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs text-indigo-400">{crit.id}</span>
                </div>
                <p className="text-slate-300 text-xs">{crit.description}</p>
                <p className="text-slate-500 text-xs mt-1 font-mono">{crit.check}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* If Fails Adjust Box */}
      {definition.if_fails_adjust && definition.if_fails_adjust.length > 0 && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <h4 className="text-sm font-medium text-yellow-400 mb-2">If Fails, Adjust</h4>
          <ul className="space-y-1">
            {definition.if_fails_adjust.map((item, idx) => (
              <li key={idx} className="text-xs text-yellow-300 flex items-start gap-2">
                <span className="text-yellow-400">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* LLM Criteria */}
      {definition.llm_criteria?.enabled && (
        <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
          <h4 className="text-sm font-medium text-purple-400 mb-2">LLM Evaluation Criteria</h4>
          <div className="text-sm">
            <div className="mb-2">
              <span className="text-slate-500">Focus Areas:</span>
              <span className="ml-2">
                {definition.llm_criteria.focus_areas?.map((area) => (
                  <span key={area} className="inline-block px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs mr-1">
                    {area}
                  </span>
                ))}
              </span>
            </div>
            {definition.llm_criteria.prompt_hint && (
              <div>
                <span className="text-slate-500">Prompt Hint:</span>
                <p className="text-slate-300 text-xs mt-1 italic">{definition.llm_criteria.prompt_hint}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Setup/Scenarios */}
      {definition.setup && (
        <div className="p-3 bg-slate-700/30 rounded-lg">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Test Setup</h4>
          {definition.setup.note && (
            <p className="text-xs text-slate-400 mb-2">{definition.setup.note}</p>
          )}

          {/* Scenarios for DIR tests */}
          {(definition.setup.scenario_a || definition.setup.scenario_b) && (
            <div className="grid grid-cols-2 gap-3">
              {definition.setup.scenario_a && (
                <div className="p-2 bg-slate-800 rounded">
                  <h5 className="text-xs font-medium text-blue-400 mb-1">
                    {definition.setup.scenario_a.name || 'Scenario A'}
                  </h5>
                  <p className="text-xs text-slate-400">{definition.setup.scenario_a.description}</p>
                  {definition.setup.scenario_a.engagements && (
                    <p className="text-xs text-slate-500 mt-1">
                      {definition.setup.scenario_a.engagements.length} engagements
                    </p>
                  )}
                </div>
              )}
              {definition.setup.scenario_b && (
                <div className="p-2 bg-slate-800 rounded">
                  <h5 className="text-xs font-medium text-green-400 mb-1">
                    {definition.setup.scenario_b.name || 'Scenario B'}
                  </h5>
                  <p className="text-xs text-slate-400">{definition.setup.scenario_b.description}</p>
                  {definition.setup.scenario_b.engagements && (
                    <p className="text-xs text-slate-500 mt-1">
                      {definition.setup.scenario_b.engagements.length} engagements
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Research Note */}
      {definition.research_note && (
        <div className="p-2 bg-slate-700/30 rounded text-xs text-slate-400 italic">
          {definition.research_note}
        </div>
      )}
    </div>
  );
}

function LlmEvaluationCard({ evaluation }) {
  if (!evaluation || evaluation.error) {
    return evaluation?.error ? (
      <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
        <span className="text-red-400 text-sm">LLM Error: {evaluation.error}</span>
      </div>
    ) : null;
  }

  return (
    <div className="mt-4 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-purple-300 flex items-center gap-2">
          <span className="text-purple-400">✨</span>
          LLM Evaluation (Gemini)
        </h4>
        <span className="text-lg font-bold text-purple-400">
          {evaluation.quality_score}/5
        </span>
      </div>

      {/* Summary */}
      <p className="text-slate-300 text-sm mb-3">{evaluation.summary}</p>

      {/* Observations */}
      {evaluation.observations?.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-medium text-slate-400 mb-1">Observations</h5>
          <ul className="space-y-1">
            {evaluation.observations.map((obs, idx) => (
              <li key={idx} className="text-xs text-slate-400 flex items-start gap-2">
                <span className="text-purple-400 mt-0.5">•</span>
                <span>{obs}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggestions */}
      {evaluation.suggestions?.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-slate-400 mb-1">Suggestions</h5>
          <ul className="space-y-1">
            {evaluation.suggestions.map((sug, idx) => (
              <li key={idx} className="text-xs text-slate-400 flex items-start gap-2">
                <span className="text-yellow-400 mt-0.5">→</span>
                <span>{sug}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {evaluation.evaluated_at && (
        <p className="text-xs text-slate-500 mt-2">
          Evaluated: {new Date(evaluation.evaluated_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}

function CriterionCard({ criterion: cr }) {
  const [showModelBreakdown, setShowModelBreakdown] = useState(false);
  const hasScalarScore = cr.score !== undefined;
  const isMultiLlm = cr.criterion_type === 'llm' && cr.model_results;
  const hasLowConsensus = cr.flag_for_review || (cr.consensus_level && !['STRONG', 'GOOD'].includes(cr.consensus_level));

  return (
    <div
      className={`p-3 rounded-lg text-sm ${cr.passed
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
          {/* LLM Judge indicator */}
          {cr.criterion_id?.startsWith('llm_') && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
              LLM Judge
            </span>
          )}
          {/* Consensus level badge */}
          {cr.consensus_level && (
            <span className={`text-xs px-1.5 py-0.5 rounded ${cr.consensus_level === 'STRONG' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
              cr.consensus_level === 'GOOD' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                cr.consensus_level === 'PARTIAL' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}>
              {cr.consensus_level}
            </span>
          )}
          {/* Low consensus warning */}
          {hasLowConsensus && (
            <span className="text-yellow-400" title="Low consensus between models - review recommended">
              ⚠️
            </span>
          )}
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

      {/* Multi-Model Breakdown */}
      {isMultiLlm && (
        <div className="mt-2">
          <button
            onClick={() => setShowModelBreakdown(!showModelBreakdown)}
            className="text-xs text-purple-400 hover:text-purple-300"
          >
            {showModelBreakdown ? '▼' : '▶'} Model Breakdown ({Object.keys(cr.model_results).length} models)
          </button>

          {showModelBreakdown && (
            <div className="mt-2 space-y-3 pl-3 border-l-2 border-purple-500/30">
              {Object.entries(cr.model_results).map(([provider, modelResult]) => {
                const samples = modelResult.samples || [];
                const meanScore = modelResult.mean_score || 0;
                const std = modelResult.std || 0;
                const reasoningSamples = modelResult.reasoning_samples || [];

                return (
                  <div key={provider} className="text-xs border-b border-slate-700/50 pb-2 last:border-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-300 capitalize font-semibold">{provider}:</span>
                      <span className="text-slate-200 font-mono">
                        {meanScore.toFixed(1)}/10 (σ={std.toFixed(2)})
                      </span>
                    </div>
                    <div className="text-slate-500 text-xs mb-1">
                      Samples: {samples.map(s => s.toFixed(1)).join(', ')}
                    </div>
                    {reasoningSamples.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {reasoningSamples.map((reasoning, idx) => (
                          <div key={idx} className="text-slate-400 text-xs italic bg-slate-800/50 p-2 rounded">
                            <span className="text-slate-500 font-semibold">Sample {idx + 1}:</span> {reasoning}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
              {cr.cross_model_std !== undefined && (
                <div className="text-xs text-purple-400 mt-1 pt-1 border-t border-purple-500/20">
                  Cross-model std: {cr.cross_model_std.toFixed(2)} (final score is mean of model means)
                </div>
              )}
            </div>
          )}
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
        className={`h-full rounded-full transition-all duration-300 ${score >= threshold
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
    <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${score >= 8
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
    <div className={`rounded-xl p-4 border ${overallScore >= 8
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
            <div className={`text-center p-3 rounded ${overallScore >= 8
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
                  className={`text-xs px-2 py-1 rounded font-mono ${score >= 8
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
            {report.context.llm_providers && report.context.llm_providers.length > 0 && (
              <p className="text-xs text-purple-400 mt-1">
                LLM Judges: {report.context.llm_providers.join(', ')} ({report.context.evaluation_mode || 'multi_llm'})
              </p>
            )}
          </div>
        )}

        {/* Algorithm Config Snapshot */}
        {report.algorithm_config?.config_snapshot && (
          <div className="mt-4 pt-4 border-t border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-blue-400">Algorithm Configuration</span>
              <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                Snapshot
              </span>
            </div>
            <details className="text-xs">
              <summary className="cursor-pointer text-slate-400 hover:text-slate-300">
                View Full Config
              </summary>
              <pre className="mt-2 bg-slate-900 p-3 rounded border border-slate-700 overflow-x-auto text-slate-300">
                {JSON.stringify(report.algorithm_config.config_snapshot, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {(report.results || []).map((result, idx) => (
          <div
            key={idx}
            className={`bg-slate-800 border rounded-lg p-4 ${result.passed ? 'border-green-500/30' : 'border-red-500/30'
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
              {result.criteria_results?.map((cr, cIdx) => {
                const isLlm = cr.criterion_id?.startsWith('llm_');
                return (
                  <span
                    key={cIdx}
                    className={`text-xs px-2 py-1 rounded ${isLlm
                      ? (cr.passed
                        ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                        : 'bg-purple-500/20 text-red-400 border border-red-500/30')
                      : (cr.passed
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400')
                      }`}
                    title={`${cr.details} | Score: ${cr.score?.toFixed(1)}/${cr.threshold}${isLlm ? ' | LLM Judge' : ''}`}
                  >
                    {isLlm && '🤖 '}{cr.criterion_id}: {cr.score !== undefined ? `${cr.score?.toFixed(1)}` : (cr.passed ? '✓' : '✗')}
                  </span>
                );
              })}
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
