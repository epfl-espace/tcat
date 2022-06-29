/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        '../templates/**/*.html',
        './js/**/*.js'
    ],
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
        },
        maxHeight: {
            'screen-1/2': '50vh',
            'screen-1/3': '33vh',
            'screen-1/4': '25vh',
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
    plugins: [
        require('daisyui')
    ],
    daisyui: {
        styled: true,
        base: true,
        utils: true,
        logs: true,
        rtl: false,
        prefix: "",
        themes: ["emerald", "dracula"],
    },
}