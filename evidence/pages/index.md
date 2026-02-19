---
title: Git Metrics Detector - Analytics
---

# Git Metrics Detector

Overview of all analyzed repositories and their discovered metrics.

<BigValue
    data={git_metrics.workspaces}
    value=id
    agg=count
    title="Total Workspaces"
/>

<BigValue
    data={git_metrics.all_metrics}
    value=id
    agg=count
    title="Total Metrics"
/>

## Metrics by Category

<BarChart
    data={git_metrics.metrics_by_category}
    x=category
    y=count
    colorPalette={['#2563eb', '#059669', '#7c3aed', '#d97706', '#dc2626', '#6b7280']}
    title="Distribution of Metrics by Category"
/>

## Metrics by Workspace

<BarChart
    data={git_metrics.metrics_by_workspace}
    x=workspace
    y=count
    series=category
    type=stacked
    colorPalette={['#2563eb', '#059669', '#7c3aed', '#d97706', '#dc2626', '#6b7280']}
    title="Metrics per Workspace (by Category)"
/>

## Data Type Distribution

<BarChart
    data={git_metrics.datatype_distribution}
    x=data_type
    y=count
    title="Metric Data Types"
    colorPalette={['#a78bfa']}
/>

## All Metrics

<DataTable
    data={git_metrics.all_metrics}
    search=true
    rows=25
>
    <Column id=workspace_name title="Workspace"/>
    <Column id=name title="Metric"/>
    <Column id=category title="Category"/>
    <Column id=data_type title="Type"/>
    <Column id=description title="Description"/>
    <Column id=suggested_source title="Source"/>
</DataTable>

## Analysis Jobs

<DataTable
    data={git_metrics.analysis_jobs}
    search=true
    rows=10
>
    <Column id=repo_name title="Repository"/>
    <Column id=status title="Status"/>
    <Column id=total_files title="Files"/>
    <Column id=analyzed_files title="Analyzed"/>
    <Column id=created_at title="Started"/>
    <Column id=completed_at title="Completed"/>
    <Column id=error_message title="Error"/>
</DataTable>
