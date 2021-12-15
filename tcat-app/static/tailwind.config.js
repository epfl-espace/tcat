module.exports = {
    darkMode: 'class',
    purge: {
        enabled: true,
        content: [
            '../templates/**/*.html',
            './js/**/*.js'
        ],
    },
    theme: {
        extend: {
            animation: {
                'spin-slow': 'spin 2s linear infinite'
            }
        },
        maxWidth: {
            '1/4': '25%',
            '45/100': '45%',
            '1/2': '50%',
            '3/4': '75%',
            '95/100': '95%'
        }
    },
    variants: {
        extend: {
            transform: ['dark'],
            translate: ['dark'],
            opacity: ['disabled'],
            backgroundColor: ['disabled', 'hover', 'dark'],
            cursor: ['hover', 'disabled', 'dark']
        }
    },
    plugins: [],
}