import React, { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area, RadialBarChart, RadialBar } from 'recharts';
import { Users, Code, Activity, Server, GitBranch, AlertCircle, CheckCircle } from 'lucide-react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

const WorkspaceDashboard = ({ metrics }) => {

  const kpis = useMemo(() => {
    return {
      generationLatency: metrics.find(m => m.metric === "End-to-End Video Generation Latency"),
      successfulGenerations: metrics.find(m => m.metric === "Successful Avatar Generation Count"),
      errorRate: metrics.find(m => m.metric === "Video Generation Error Rate"),
    };
  }, [metrics]);

  const performanceMetrics = useMemo(() => {
    return metrics.filter(m => m.category === "performance");
  }, [metrics]);

  const contentMetrics = useMemo(() => {
    return metrics.filter(m => m.category === "content");
  }, [metrics]);

  const engagementMetrics = useMemo(() => {
    return metrics.filter(m => m.category === "engagement");
  }, [metrics]);

  const technicalMetrics = useMemo(() => {
    return metrics.filter(m => m.category === "technical");
  }, [metrics]);

  const cacheHitRate = metrics.find(m => m.metric === "Cache Hit Rate (Generated Videos)")?.value || 0;

  return (
    <div className="container mx-auto p-4 bg-white">
      <h1 className="text-2xl font-bold mb-4 text-gray-800">Avatar Project (Lite Version) Dashboard</h1>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
          <h2 className="text-lg font-semibold text-gray-800">Generation Latency</h2>
          <p className="text-3xl font-bold text-red-500">{kpis.generationLatency?.display_value || 'N/A'}</p>
          <p className="text-gray-500">{kpis.generationLatency?.description}</p>
        </div>
        <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
          <h2 className="text-lg font-semibold text-gray-800">Successful Generations</h2>
          <p className="text-3xl font-bold text-red-500">{kpis.successfulGenerations?.display_value || 'N/A'}</p>
          <p className="text-gray-500">{kpis.successfulGenerations?.description}</p>
        </div>
        <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
          <h2 className="text-lg font-semibold text-gray-800">Error Rate</h2>
          <p className="text-3xl font-bold text-red-500">{kpis.errorRate?.display_value || 'N/A'}</p>
          <p className="text-gray-500">{kpis.errorRate?.description}</p>
        </div>
      </div>

      {/* Performance Metrics */}
      <h2 className="text-xl font-semibold mb-2 text-gray-800">Performance</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {performanceMetrics.map(metric => (
          <div key={metric.metric} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
            <h3 className="text-md font-semibold text-gray-800">{metric.metric}</h3>
            <p className="text-gray-500">{metric.description}</p>
            <p className="text-red-500">{metric.display_value}</p>
          </div>
        ))}
      </div>

      {/* Cache Hit Rate Radial Bar Chart */}
      <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-4 mb-6">
        <h2 className="text-xl font-semibold mb-2 text-gray-800">Cache Hit Rate</h2>
        <ResponsiveContainer width="100%" height={200}>
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="20%"
            outerRadius="80%"
            data={[{ value: cacheHitRate }]}
            startAngle={90}
            endAngle={-270}
          >
            <RadialBar background dataKey="value" fill="#ef4444" />
            <Tooltip />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="text-center text-gray-500">{cacheHitRate}%</div>
      </div>

      {/* Content Metrics */}
      <h2 className="text-xl font-semibold mb-2 text-gray-800">Content</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {contentMetrics.map(metric => (
          <div key={metric.metric} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
            <h3 className="text-md font-semibold text-gray-800">{metric.metric}</h3>
            <p className="text-gray-500">{metric.description}</p>
            <p className="text-red-500">{metric.display_value}</p>
          </div>
        ))}
      </div>

      {/* Engagement Metrics */}
      <h2 className="text-xl font-semibold mb-2 text-gray-800">Engagement</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {engagementMetrics.map(metric => (
          <div key={metric.metric} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
            <h3 className="text-md font-semibold text-gray-800">{metric.metric}</h3>
            <p className="text-gray-500">{metric.description}</p>
            <p className="text-red-500">{metric.display_value}</p>
          </div>
        ))}
      </div>

      {/* Technical Metrics */}
      <h2 className="text-xl font-semibold mb-2 text-gray-800">Technical</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {technicalMetrics.map(metric => (
          <div key={metric.metric} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
            <h3 className="text-md font-semibold text-gray-800">{metric.metric}</h3>
            <p className="text-gray-500">{metric.description}</p>
            <p className="text-red-500">{metric.display_value}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkspaceDashboard;