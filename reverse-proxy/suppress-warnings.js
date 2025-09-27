// TipTap 경고 억제 스크립트
(function() {
    'use strict';

    // console.warn 오버라이드
    const originalWarn = console.warn;
    console.warn = function(...args) {
        const message = args.join(' ');

        // TipTap 중복 확장 경고 억제
        if (message.includes('[tiptap warn]') && message.includes('Duplicate extension names')) {
            return; // 경고를 억제하고 아무것도 출력하지 않음
        }

        // 다른 경고는 그대로 출력
        return originalWarn.apply(console, args);
    };

    console.log('TipTap warnings suppressed for cleaner console');
})();