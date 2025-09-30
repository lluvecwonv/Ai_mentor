<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	import Chat from '$lib/components/chat/Chat.svelte';

	// 새로고침(F5) 감지 시 홈으로 이동
	onMount(() => {
		if (typeof window !== 'undefined' && window.performance) {
			const navigationType = window.performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
			if (navigationType && navigationType.type === 'reload') {
				goto('/');
			}
		}
	});
</script>

<Chat chatIdProp={$page.params.id} />
