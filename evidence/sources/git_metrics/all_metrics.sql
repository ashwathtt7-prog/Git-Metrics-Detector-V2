SELECT
    m.id,
    m.name,
    m.description,
    COALESCE(m.category, 'uncategorized') as category,
    m.data_type,
    m.suggested_source,
    m.display_order,
    w.name as workspace_name,
    w.repo_url
FROM metrics m
JOIN workspaces w ON m.workspace_id = w.id
ORDER BY w.name, m.category, m.display_order
