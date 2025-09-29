<script lang="ts">
	import { onMount } from 'svelte';

	export let submitPrompt;

	const suggestions = [
		{
			title: '옵션 거래 설명',
			subtitle: "주식 매매는 알고 있어요",
			prompt: "옵션 거래에 대해 설명해주세요. 주식 매매는 알고 있어요"
		},
		{
			title: '로마 제국 재미있는 사실',
			subtitle: '역사에 대한 흥미로운 이야기',
			prompt: '로마 제국에 대한 재미있는 사실을 알려주세요'
		},
		{
			title: '어휘 공부 도움',
			subtitle: '대학 입학 시험을 위한',
			prompt: '대학 입학 시험을 위한 어휘 공부를 도와주세요'
		}
	];

	let searchQuery = '';

	function handleSubmit() {
		if (!searchQuery.trim()) return;
		submitPrompt(searchQuery.trim());
		searchQuery = '';
	}

	function selectSuggestion(prompt: string) {
		submitPrompt(prompt);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSubmit();
		}
	}

	onMount(() => {
		// 컴포넌트 마운트 시 검색창에 포커스
		const searchInput = document.getElementById('ai-mentor-search');
		if (searchInput) {
			searchInput.focus();
		}
	});
</script>

<!-- AI Mentor 랜딩 페이지 -->
<div class="w-full max-w-[820px] mx-auto min-h-[70vh] flex flex-col items-center justify-center gap-7 px-4">
	<!-- 로고 -->
	<div class="w-14 h-14 rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 flex items-center justify-center font-bold text-xl">
		AI
	</div>

	<!-- 제목 -->
	<h1 class="text-4xl md:text-5xl font-bold tracking-tight text-center text-gray-900 dark:text-white">
		AI Mentor
	</h1>

	<!-- 검색바 -->
	<div class="w-full border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-4 flex items-center gap-3 shadow-sm hover:shadow-md transition-shadow bg-white dark:bg-gray-800">
		<input
			id="ai-mentor-search"
			class="flex-1 outline-none text-lg bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
			bind:value={searchQuery}
			placeholder="무엇을 도와드릴까요?"
			on:keydown={handleKeydown}
		/>
		<button
			class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
			aria-label="음성 입력"
			title="음성 입력"
		>
			🎙️
		</button>
		<button
			class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
			aria-label="음성 출력"
			title="음성 출력"
		>
			🔊
		</button>
		{#if searchQuery.trim()}
			<button
				class="p-2 hover:bg-blue-100 dark:hover:bg-blue-900 rounded-lg transition-colors text-blue-600 dark:text-blue-400"
				on:click={handleSubmit}
				title="검색"
			>
				↵
			</button>
		{/if}
	</div>

	<!-- 추천 제안 -->
	<div class="w-full">
		<h4 class="text-sm text-gray-500 dark:text-gray-400 mb-3 font-medium">⚡ 제안</h4>
		<div class="grid gap-3">
			{#each suggestions as suggestion}
				<button
					class="text-left border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 transition-all duration-200 group bg-white dark:bg-gray-800"
					on:click={() => selectSuggestion(suggestion.prompt)}
				>
					<div class="block text-gray-900 dark:text-white group-hover:text-gray-700 dark:group-hover:text-gray-200 font-semibold">
						{suggestion.title}
					</div>
					<div class="text-gray-600 dark:text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300 text-sm mt-1">
						{suggestion.subtitle}
					</div>
				</button>
			{/each}
		</div>
	</div>
</div>