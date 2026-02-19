SELECT
    w.name as workspace,
    COALESCE(m.category, 'uncategorized') as category,
    COUNT(*) as count
FROM metrics m
JOIN workspaces w ON m.workspace_id = w.id
GROUP BY w.name, m.category
ORDER BY w.name, count DESC
