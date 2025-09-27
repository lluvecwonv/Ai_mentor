// AI Mentor UI Cleanup Script
// 마이크, 음성, 불필요한 버튼들 완전 제거

(function() {
    'use strict';

    console.log('🤖 AI Mentor UI Cleanup 시작');

    // 숨길 요소들의 선택자들
    const HIDE_SELECTORS = [
        // 마이크 관련
        'button[title*="voice" i]',
        'button[title*="mic" i]',
        'button[title*="microphone" i]',
        'button[title*="record" i]',
        'button[title*="audio" i]',
        'button[title*="speak" i]',
        'button[title*="speech" i]',
        'button[aria-label*="voice" i]',
        'button[aria-label*="mic" i]',
        'button[aria-label*="microphone" i]',
        'button[aria-label*="record" i]',
        'button[aria-label*="audio" i]',
        'button[aria-label*="speak" i]',
        'button[aria-label*="speech" i]',
        '[class*="voice" i]:not(.message)',
        '[class*="mic" i]:not(.message)',
        '[class*="microphone" i]:not(.message)',
        '[class*="audio" i]:not(.message)',
        '[class*="speech" i]:not(.message)',
        '[class*="record" i]:not(.message)',
        '[id*="voice" i]',
        '[id*="mic" i]',
        '[id*="microphone" i]',
        '[id*="audio" i]',
        '[id*="speech" i]',
        '[id*="record" i]',

        // SVG 아이콘들
        'svg[class*="microphone" i]',
        'svg[class*="mic" i]',
        'svg[class*="voice" i]',
        'svg[class*="audio" i]',
        'svg[class*="speech" i]',
        'svg[class*="record" i]',

        // 특정 아이콘 클래스들
        '.fa-microphone',
        '.fa-microphone-alt',
        '.lucide-microphone',

        // OpenWebUI 상단바/네비게이션 완전 제거
        'nav',
        '.navbar',
        '.nav',
        '.navigation',
        'header',
        '.header',
        '.top-header',
        '.app-header',
        '[class*="navbar"]',
        '[class*="nav-"]',
        '[class*="-nav"]',
        '[class*="header"]',
        '[class*="top-"]',
        '[class*="-top"]',
        '[id*="nav"]',
        '[id*="header"]',
        '[id*="top"]',

        // 관리자/설정 링크와 버튼들
        'button[title*="Settings" i]',
        'button[title*="Admin" i]',
        'button[title*="Models" i]',
        'button[aria-label*="Settings" i]',
        'button[aria-label*="Admin" i]',
        'button[aria-label*="Models" i]',
        'a[href*="/admin"]',
        'a[href*="/settings"]',
        'a[href*="/models"]',
        '.sidebar button[title*="Settings" i]',
        '.sidebar a[href*="admin"]',
        '.sidebar a[href*="settings"]',
        '[class*="settings"]',
        '[class*="admin"]',
        '[class*="model-settings"]',

        // 로그인/계정 관련
        'a[href*="/login"]',
        'a[href*="/signup"]',
        'a[href*="/auth"]',
        'button[title*="login" i]',
        'button[title*="logout" i]',
        'button[title*="sign" i]',
        '[class*="login"]',
        '[class*="signup"]',
        '[class*="account"]',
        '[class*="profile"]',
        '.lucide-mic',
        '.tabler-microphone',
        '.tabler-mic',

        // + 버튼 (파일 업로드 등 불필요한 기능)
        'button[title*="attach" i]',
        'button[title*="upload" i]',
        'button[title*="file" i]',
        'button[aria-label*="attach" i]',
        'button[aria-label*="upload" i]',
        'button[aria-label*="file" i]',

        // 설정 관련 버튼들
        'button[title*="settings" i]',
        'button[title*="admin" i]',
        'button[title*="models" i]',
        'button[title*="workspace" i]',
        'button[title*="profile" i]',
        'button[title*="knowledge" i]',
        'button[title*="playground" i]',
        'button[title*="tools" i]',
        'button[title*="functions" i]',
        'button[aria-label*="settings" i]',
        'button[aria-label*="admin" i]',
        'button[aria-label*="models" i]',
        'button[aria-label*="workspace" i]',
        'button[aria-label*="profile" i]',
        'button[aria-label*="knowledge" i]',
        'button[aria-label*="playground" i]',
        'button[aria-label*="tools" i]',
        'button[aria-label*="functions" i]',

        // 상단 네비게이션 특정 요소들
        'nav button[title*="settings" i]',
        'nav button[title*="admin" i]',
        'nav button[title*="models" i]',
        'nav button[title*="workspace" i]',
        'nav button[title*="profile" i]',
        'nav button[title*="knowledge" i]',
        'nav button[title*="playground" i]',
        'nav button[title*="tools" i]',
        'nav button[title*="functions" i]',
        'header button[title*="settings" i]',
        'header button[title*="admin" i]',
        'header button[title*="models" i]',
        'header button[title*="workspace" i]',
        'header button[title*="profile" i]',
        'header button[title*="knowledge" i]',
        'header button[title*="playground" i]',
        'header button[title*="tools" i]',
        'header button[title*="functions" i]',

        // 사이드바/메뉴 항목들
        '.sidebar button',
        '.menu button[title*="settings" i]',
        '.menu button[title*="admin" i]',
        '.menu button[title*="models" i]',
        '.menu button[title*="workspace" i]',
        '.menu button[title*="profile" i]',
        '.menu button[title*="knowledge" i]',
        '.menu button[title*="playground" i]',
        '.menu button[title*="tools" i]',
        '.menu button[title*="functions" i]',

        // 드롭다운 메뉴 항목들
        '.dropdown-menu button',
        '.dropdown-content button',
        'ul[role="menu"] button',
        'div[role="menu"] button',

        // 햄버거 메뉴나 설정 아이콘들
        'button[class*="menu" i]:not([class*="send" i])',
        'button[class*="setting" i]',
        'button[class*="config" i]',
        'button[class*="gear" i]',
        'button[class*="cog" i]',

        // 토글 스위치들
        '.voice-toggle',
        '.audio-toggle',
        '.mic-toggle',
        '.speech-toggle',
        '.tts-toggle',
        '.stt-toggle'
    ];

    // 공개 모드: 로그인/회원가입/계정 관련 UI 제거
    const AUTH_HIDE_SELECTORS = [
        'a[href*="/login"]',
        'a[href*="/signup"]',
        'a[href*="/auth"]',
        'a[href*="/logout"]',
        'button[title*="login" i]',
        'button[title*="logout" i]',
        'button[title*="sign" i]',
        'button[aria-label*="login" i]',
        'button[aria-label*="logout" i]',
        'button[aria-label*="sign" i]',
        '[class*="login" i]',
        '[class*="signup" i]',
        '[class*="signin" i]',
        '[class*="account" i]',
        '[class*="profile" i]'
    ];

    // 요소 숨기기 함수
    function hideElement(element) {
        if (element && element.style) {
            element.style.display = 'none';
            element.style.visibility = 'hidden';
            element.style.opacity = '0';
            element.style.pointerEvents = 'none';
            element.style.position = 'absolute';
            element.style.left = '-9999px';
            element.setAttribute('data-ai-mentor-hidden', 'true');
        }
    }

    // 전송 버튼 스타일링 함수
    function styleSendButton(button) {
        if (button && !button.hasAttribute('data-ai-mentor-styled')) {
            button.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            button.style.color = 'white';
            button.style.border = 'none';
            button.style.borderRadius = '8px';
            button.style.padding = '10px 20px';
            button.style.fontWeight = '600';
            button.style.cursor = 'pointer';
            button.style.minWidth = '60px';
            button.style.display = 'inline-flex';
            button.style.alignItems = 'center';
            button.style.justifyContent = 'center';
            button.setAttribute('data-ai-mentor-styled', 'true');

            // 호버 효과
            button.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-1px)';
                this.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.3)';
            });

            button.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            });

            console.log('✅ 전송 버튼 스타일링 적용:', button);
        }
    }

    // 전송 버튼 찾기
    const SEND_BUTTON_SELECTORS = [
        'button[type="submit"]',
        'button[title*="send" i]',
        'button[aria-label*="send" i]',
        'button[title*="전송" i]',
        'button[aria-label*="전송" i]',
        'form button[type="submit"]',
        '.chat-input button[type="submit"]',
        '.message-input button[type="submit"]',
        'button[class*="send" i]',
        'button[class*="submit" i]'
    ];

    // DOM 정리 실행
    function cleanupUI() {
        let hiddenCount = 0;
        let styledCount = 0;

        // 불필요한 요소들 숨기기
        HIDE_SELECTORS.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(element => {
                    if (!element.hasAttribute('data-ai-mentor-hidden')) {
                        hideElement(element);
                        hiddenCount++;
                    }
                });
            } catch (e) {
                // 잘못된 선택자 무시
            }
        });

        // 인증 관련 UI 요소 숨김
        AUTH_HIDE_SELECTORS.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(element => {
                    if (!element.hasAttribute('data-ai-mentor-hidden')) {
                        hideElement(element);
                        hiddenCount++;
                    }
                });
            } catch (e) {
                // 잘못된 선택자 무시
            }
        });

        // 특정 아이콘을 가진 버튼들 숨기기 (설정, 메뉴 아이콘 등)
        const iconButtons = document.querySelectorAll('button svg, button i, button [class*="icon"]');
        iconButtons.forEach(icon => {
            const button = icon.closest('button');
            if (button && !button.hasAttribute('data-ai-mentor-hidden')) {
                const iconClass = icon.className || icon.getAttribute('class') || '';
                const iconContent = icon.textContent || '';

                // 설정, 메뉴, 기어, 햄버거 아이콘 등을 가진 버튼 숨기기
                if (iconClass.includes('gear') ||
                    iconClass.includes('cog') ||
                    iconClass.includes('setting') ||
                    iconClass.includes('menu') ||
                    iconClass.includes('hamburger') ||
                    iconClass.includes('bars') ||
                    iconClass.includes('ellipsis') ||
                    iconClass.includes('dots') ||
                    iconContent.includes('⚙') ||
                    iconContent.includes('☰') ||
                    iconContent.includes('⋮') ||
                    iconContent.includes('⋯')) {

                    // 하지만 전송 버튼은 제외
                    const buttonText = (button.textContent || button.title || button.getAttribute('aria-label') || '').toLowerCase();
                    if (!buttonText.includes('send') && !buttonText.includes('전송') && !buttonText.includes('submit')) {
                        hideElement(button);
                        hiddenCount++;
                    }
                }
            }
        });

        // 상단 네비게이션의 특정 링크들 숨기기
        const navLinks = document.querySelectorAll('nav a, header a, .navbar a');
        navLinks.forEach(link => {
            const href = link.getAttribute('href') || '';
            const text = link.textContent.toLowerCase() || '';

            if (href.includes('/admin') ||
                href.includes('/settings') ||
                href.includes('/models') ||
                href.includes('/workspace') ||
                href.includes('/profile') ||
                href.includes('/knowledge') ||
                href.includes('/playground') ||
                href.includes('/tools') ||
                href.includes('/functions') ||
                text.includes('설정') ||
                text.includes('관리') ||
                text.includes('모델') ||
                text.includes('워크스페이스') ||
                text.includes('프로필')) {

                if (!link.hasAttribute('data-ai-mentor-hidden')) {
                    hideElement(link);
                    hiddenCount++;
                }
            }
        });

        // 전송 버튼 스타일링
        SEND_BUTTON_SELECTORS.forEach(selector => {
            try {
                const buttons = document.querySelectorAll(selector);
                buttons.forEach(button => {
                    // 마이크나 음성 관련이 아닌 버튼만 스타일링
                    const buttonText = (button.textContent || button.title || button.getAttribute('aria-label') || '').toLowerCase();
                    const hasVoiceIcon = button.querySelector('svg[class*="mic"], svg[class*="voice"], svg[class*="audio"]');

                    if (!buttonText.includes('voice') && !buttonText.includes('mic') && !buttonText.includes('audio') && !hasVoiceIcon) {
                        styleSendButton(button);
                        styledCount++;
                    }
                });
            } catch (e) {
                // 잘못된 선택자 무시
            }
        });

        // OpenWebUI 특정 요소들 추가 정리
        // 상단 툴바나 네비게이션 바의 버튼들
        const toolbarButtons = document.querySelectorAll(
            '.toolbar button, .nav-bar button, .top-bar button, ' +
            '[class*="toolbar"] button, [class*="nav-bar"] button, [class*="top-bar"] button, ' +
            '[role="toolbar"] button, [role="navigation"] button'
        );

        toolbarButtons.forEach(button => {
            if (!button.hasAttribute('data-ai-mentor-hidden')) {
                const buttonText = (button.textContent || button.title || button.getAttribute('aria-label') || '').toLowerCase();
                const buttonClass = button.className.toLowerCase();

                // 새 채팅, 설정, 메뉴 등의 버튼은 숨기되 전송 버튼은 보존
                if (buttonText.includes('new chat') ||
                    buttonText.includes('새 채팅') ||
                    buttonText.includes('settings') ||
                    buttonText.includes('설정') ||
                    buttonText.includes('menu') ||
                    buttonText.includes('메뉴') ||
                    buttonClass.includes('menu') ||
                    buttonClass.includes('setting') ||
                    (buttonText === '' && button.querySelector('svg'))) { // 아이콘만 있는 버튼

                    // 전송/제출 관련이 아닌 경우에만 숨김
                    if (!buttonText.includes('send') && !buttonText.includes('전송') &&
                        !buttonText.includes('submit') && !buttonClass.includes('send')) {
                        hideElement(button);
                        hiddenCount++;
                    }
                }
            }
        });

        // 드롭다운이나 팝업 메뉴 아이템들
        const menuItems = document.querySelectorAll(
            '.menu-item, .dropdown-item, [role="menuitem"], [role="option"], ' +
            'li[class*="menu"], li[class*="item"]'
        );

        menuItems.forEach(item => {
            if (!item.hasAttribute('data-ai-mentor-hidden')) {
                const itemText = item.textContent.toLowerCase();

                if (itemText.includes('settings') ||
                    itemText.includes('admin') ||
                    itemText.includes('models') ||
                    itemText.includes('workspace') ||
                    itemText.includes('profile') ||
                    itemText.includes('설정') ||
                    itemText.includes('관리') ||
                    itemText.includes('모델') ||
                    itemText.includes('워크스페이스')) {

                    hideElement(item);
                    hiddenCount++;
                }
            }
        });

        // 헤더 내부에서 네비게이션바 위의 요소들을 숨김
        // (header 자식들 중 nav 이전의 형제 요소들을 비활성화)
        document.querySelectorAll('header').forEach(header => {
            const nav = header.querySelector('nav, [role="navigation"]');
            if (!nav) return;

            if (nav.parentElement === header) {
                let child = header.firstElementChild;
                while (child && child !== nav) {
                    if (!child.hasAttribute('data-ai-mentor-hidden')) {
                        hideElement(child);
                        hiddenCount++;
                    }
                    child = child.nextElementSibling;
                }
            } else {
                const container = nav.parentElement;
                let child = header.firstElementChild;
                while (child && child !== container) {
                    if (!child.hasAttribute('data-ai-mentor-hidden')) {
                        hideElement(child);
                        hiddenCount++;
                    }
                    child = child.nextElementSibling;
                }
            }
        });

        // 좌측 사이드바 전체 숨기기 (채팅 목록 등)
        const sidebars = document.querySelectorAll(
            '.sidebar, .side-panel, [class*="sidebar"], [class*="side-panel"], ' +
            'aside, nav[class*="side"]'
        );

        sidebars.forEach(sidebar => {
            if (!sidebar.hasAttribute('data-ai-mentor-hidden')) {
                hideElement(sidebar);
                hiddenCount++;
            }
        });

        // 상단바/헤더 영역 강제 제거 (더 강력한 방법)
        const topElements = document.querySelectorAll(
            'header, .header, .top-header, .app-header, .main-header, .page-header, ' +
            'nav, .navbar, .nav, .navigation, .navbar-nav, .navbar-container, ' +
            '[class*="navbar"], [class*="nav-"], [class*="-nav"], [class*="header"], ' +
            '[class*="top-"], [class*="-top"], [class*="bar"]:not(.progress-bar), ' +
            '[id*="nav"], [id*="header"], [id*="top"], [id*="bar"]:not([id*="progress"])'
        );

        topElements.forEach(element => {
            // 진행률 바나 스크롤바는 제외
            if (!element.className?.includes('progress') &&
                !element.className?.includes('scroll') &&
                !element.id?.includes('progress') &&
                !element.hasAttribute('data-ai-mentor-hidden')) {

                hideElement(element);
                hiddenCount++;

                // 부모 요소의 패딩/마진도 조정
                if (element.parentElement) {
                    element.parentElement.style.paddingTop = '0px';
                    element.parentElement.style.marginTop = '0px';
                }
            }
        });

        // body와 main 콘텐츠의 상단 간격 제거
        document.body.style.paddingTop = '0px';
        document.body.style.marginTop = '0px';

        const mainContents = document.querySelectorAll(
            'main, .main, .content, .container, .wrapper, [class*="main"], [class*="content"]'
        );

        mainContents.forEach(main => {
            main.style.paddingTop = '0px';
            main.style.marginTop = '0px';
        });

        if (hiddenCount > 0 || styledCount > 0) {
            console.log(`🧹 UI 정리 완료 - 숨긴 요소: ${hiddenCount}개, 스타일링한 버튼: ${styledCount}개`);
        }
    }

    // 즉시 실행
    cleanupUI();

    // DOM 변경 감지 및 정리
    const observer = new MutationObserver((mutations) => {
        let shouldCleanup = false;

        mutations.forEach(mutation => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                shouldCleanup = true;
            }
        });

        if (shouldCleanup) {
            setTimeout(cleanupUI, 100); // 약간의 딜레이 후 정리
        }
    });

    // DOM 감시 시작
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // 페이지 로드 완료 후에도 한 번 더 실행
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', cleanupUI);
    }

    window.addEventListener('load', () => {
        setTimeout(cleanupUI, 1000); // 1초 후 한 번 더
        setTimeout(cleanupUI, 3000); // 3초 후 한 번 더
    });

    console.log('🤖 AI Mentor UI Cleanup 설정 완료');
})();
