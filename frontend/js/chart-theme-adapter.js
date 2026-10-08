/* ============================================================
   KitchenIQ — Chart.js Theme Adapter
   Auto-updates all charts when theme changes.
   ============================================================ */

(function () {
    // Update Chart.js defaults on theme change
    function updateChartDefaults() {
        if (!window.Chart) return;

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        Chart.defaults.color = isDark ? '#94a3b8' : '#64748b';
        Chart.defaults.borderColor = isDark ? '#334155' : '#f1f5f9';

        // Update all active charts
        Object.values(Chart.instances).forEach(chart => {
            // Grid lines
            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(scale => {
                    if (scale.grid) {
                        scale.grid.color = isDark ? '#1e293b' : '#f1f5f9';
                    }
                    if (scale.ticks) {
                        scale.ticks.color = isDark ? '#94a3b8' : '#64748b';
                    }
                });
            }

            // Legend
            if (chart.options.plugins?.legend?.labels) {
                chart.options.plugins.legend.labels.color = isDark ? '#e2e8f0' : '#0f172a';
            }

            // Tooltip
            if (chart.options.plugins?.tooltip) {
                chart.options.plugins.tooltip.backgroundColor = isDark ? '#0f172a' : '#0f172a';
            }

            chart.update('none'); // Update without animation
        });
    }

    // Listen for theme change
    window.addEventListener('kiq:theme-changed', updateChartDefaults);

    // Initial call
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateChartDefaults);
    } else {
        updateChartDefaults();
    }
})();