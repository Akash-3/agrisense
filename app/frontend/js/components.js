/**
 * AgriSense Reusable UI Component System & Accessible Primitives
 * Standalone Design System Module (No heavy framework build step required)
 */
const UIComponents = {
    // Design System Tokens
    tokens: {
        colors: {
            primary: '#079A70',
            primaryDark: '#006B50',
            secondary: '#159B7A',
            navy: '#0D172B',
            mint: '#DDF4EC',
            slateBg: '#F8FAFC',
            border: '#E2E8F0',
            warning: '#F4A019',
            danger: '#EF5B67'
        }
    },

    // Button Component Primitive
    Button(options = {}) {
        const { label = '', icon = '', variant = 'primary', size = 'md', className = '', onClick = '', disabled = false, id = '' } = options;
        let baseClass = 'inline-flex items-center justify-center font-bold transition-all duration-200 focus-visible:outline-2 focus-visible:outline-agri-primary focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ';
        
        // Variants
        if (variant === 'primary') baseClass += 'btn-agri-primary rounded-xl ';
        else if (variant === 'secondary') baseClass += 'btn-agri-secondary rounded-xl ';
        else if (variant === 'ghost') baseClass += 'bg-transparent text-slate-600 hover:bg-slate-100 rounded-xl ';
        else if (variant === 'danger') baseClass += 'bg-red-600 hover:bg-red-700 text-white rounded-xl shadow-md ';

        // Sizes
        if (size === 'sm') baseClass += 'px-3 py-1.5 text-xs ';
        else if (size === 'md') baseClass += 'px-4 py-2.5 text-xs sm:text-sm ';
        else if (size === 'lg') baseClass += 'px-6 py-3.5 text-sm sm:text-base ';

        const iconHtml = icon ? `<i class="${icon} ${label ? 'mr-2' : ''}"></i>` : '';
        const idAttr = id ? `id="${id}"` : '';
        const clickAttr = onClick ? `onclick="${onClick}"` : '';
        const disAttr = disabled ? 'disabled' : '';

        return `<button ${idAttr} class="${baseClass} ${className}" ${clickAttr} ${disAttr}>${iconHtml}<span>${label}</span></button>`;
    },

    // Badge Component Primitive
    Badge(options = {}) {
        const { label = '', variant = 'online', icon = '', className = '' } = options;
        let badgeClass = 'badge-status ';
        if (variant === 'online') badgeClass += 'badge-online ';
        else if (variant === 'offline') badgeClass += 'badge-offline ';
        else if (variant === 'hardware') badgeClass += 'badge-hardware ';
        else if (variant === 'simulation') badgeClass += 'badge-simulation ';
        else badgeClass += 'bg-slate-100 text-slate-700 border border-slate-200 ';

        const iconHtml = icon ? `<i class="${icon}"></i>` : '';
        return `<span class="${badgeClass} ${className}">${iconHtml}<span>${label}</span></span>`;
    },

    // Card Surface Primitive
    Card(options = {}) {
        const { content = '', title = '', subtitle = '', action = '', className = '', id = '' } = options;
        const idAttr = id ? `id="${id}"` : '';
        const header = (title || subtitle || action) ? `
            <div class="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div>
                    ${subtitle ? `<span class="text-xs font-bold text-slate-400 uppercase tracking-wider">${subtitle}</span>` : ''}
                    ${title ? `<h3 class="text-base sm:text-lg font-black text-slate-900">${title}</h3>` : ''}
                </div>
                ${action ? `<div>${action}</div>` : ''}
            </div>` : '';

        return `<div ${idAttr} class="card-agri p-5 sm:p-6 ${className}">${header}${content}</div>`;
    },

    // Skeleton Loading Placeholder Primitive
    Skeleton(options = {}) {
        const { width = 'w-full', height = 'h-4', className = '' } = options;
        return `<div class="skeleton-agri ${width} ${height} ${className}"></div>`;
    },

    // Empty State Component Primitive
    EmptyState(options = {}) {
        const { title = 'No Data Available', message = 'Waiting for telemetry stream or sensor connection.', icon = 'fa-solid fa-inbox', action = '' } = options;
        return `
            <div class="p-8 text-center space-y-3 bg-slate-50/50 rounded-2xl border border-dashed border-slate-200">
                <div class="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                    <i class="${icon}"></i>
                </div>
                <div class="space-y-1">
                    <h4 class="font-bold text-slate-800 text-sm">${title}</h4>
                    <p class="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">${message}</p>
                </div>
                ${action ? `<div class="pt-2">${action}</div>` : ''}
            </div>
        `;
    },

    // Error State Component Primitive
    ErrorState(options = {}) {
        const { title = 'Service Exception', message = 'An error occurred while connecting to backend service.', onRetry = '' } = options;
        const retryBtn = onRetry ? `<button onclick="${onRetry}" class="mt-2 px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-800 font-bold text-xs transition">Retry Connection</button>` : '';
        return `
            <div class="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 flex items-start space-x-3 text-xs">
                <i class="fa-solid fa-circle-exclamation text-base text-red-500 mt-0.5"></i>
                <div class="flex-1 space-y-1">
                    <div class="font-bold text-red-900 text-sm">${title}</div>
                    <p class="text-red-700 leading-relaxed font-medium">${message}</p>
                    ${retryBtn}
                </div>
            </div>
        `;
    }
};

window.UIComponents = UIComponents;
