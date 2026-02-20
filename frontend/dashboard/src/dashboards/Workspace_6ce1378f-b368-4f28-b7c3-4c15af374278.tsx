import React, { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area, RadialBarChart, RadialBar } from 'recharts';
import { Users, Code, Activity, Server, GitBranch, AlertCircle, CheckCircle } from 'lucide-react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#ef4444'];

const WorkspaceDashboard = ({ metrics }) => {

  const kpiMetrics = useMemo(() => {
    return {
      endToEndTime: metrics.find(m => m.name === "End-to-End Avatar Generation Time"),
      generationSuccessRate: metrics.find(m => m.name === "Generation Success Rate"),
      totalGenerations: metrics.find(m => m.name === "Total Avatar Generations"),
    };
  }, [metrics]);

  const performanceMetrics = useMemo(() => {
    return metrics.filter(m => m.category === "performance" && m.name !== "End-to-End Avatar Generation Time");
  }, [metrics]);

  const engagementMetrics = useMemo(() => {
    return metrics.filter(m => m.category === "engagement");
  }, [metrics]);

  const contentMetrics = useMemo(() => {
    return metrics.filter(m => m.category === "content");
  }, [metrics]);

  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text x={x} y={y} fill="white" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="container mx-auto p-4 bg-white">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Avatar Project (Lite Version) Dashboard</h1>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">End-to-End Generation Time</h2>
          <p className="text-4xl font-bold text-red-500">{kpiMetrics.endToEndTime?.display_value || 'N/A'}</p>
          <p className="text-gray-500">{kpiMetrics.endToEndTime?.description}</p>
        </div>

        <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Generation Success Rate</h2>
          <p className="text-4xl font-bold text-red-500">{kpiMetrics.generationSuccessRate?.display_value || 'N/A'}</p>
          <p className="text-gray-500">{kpiMetrics.generationSuccessRate?.description}</p>
        </div>

        <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Total Generations</h2>
          <p className="text-4xl font-bold text-red-500">{kpiMetrics.totalGenerations?.display_value || 'N/A'}</p>
          <p className="text-gray-500">{kpiMetrics.totalGenerations?.description}</p>
        </div>
      </div>

      {/* Performance Metrics */}
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Performance Metrics</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {performanceMetrics.map((metric) => (
          <div key={metric.name} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
            <h3 className="text-md font-semibold text-gray-800 mb-2">{metric.name}</h3>
            <p className="text-gray-500">{metric.description}</p>
            <p className="text-2xl font-bold text-red-500">{metric.display_value || 'N/A'}</p>
          </div>
        ))}
      </div>

      {/* Engagement Metrics */}
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Engagement Metrics</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {engagementMetrics.map((metric) => (
          <div key={metric.name} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
            <h3 className="text-md font-semibold text-gray-800 mb-2">{metric.name}</h3>
            <p className="text-gray-500">{metric.description}</p>
            <p className="text-2xl font-bold text-red-500">{metric.display_value || 'N/A'}</p>
          </div>
        ))}
      </div>

      {/* Content Metrics */}
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Content Metrics</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {contentMetrics.map((metric) => (
          <div key={metric.name} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4">
            <h3 className="text-md font-semibold text-gray-800 mb-2">{metric.name}</h3>
            <p className="text-gray-500">{metric.description}</p>
            <p className="text-2xl font-bold text-red-500">{metric.display_value || 'N/A'}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkspaceDashboard;