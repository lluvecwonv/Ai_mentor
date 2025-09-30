<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import { config, user, models as _models, temporaryChatEnabled } from '$lib/stores';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';

	const i18n = getContext('i18n');

	export let transparentBackground = false;

	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let toolServers = [];

	let models = [];

	const selectSuggestionPrompt = async (p) => {
		let text = p;

		if (p.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch((err) => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});

			text = p.replaceAll('{{CLIPBOARD}}', clipboardText);

			console.log('Clipboard text:', clipboardText, text);
		}

		prompt = text;

		console.log(prompt);
		await tick();

		const chatInputContainerElement = document.getElementById('chat-input-container');
		const chatInputElement = document.getElementById('chat-input');

		if (chatInputContainerElement) {
			chatInputContainerElement.scrollTop = chatInputContainerElement.scrollHeight;
		}

		await tick();
		if (chatInputElement) {
			chatInputElement.focus();
			chatInputElement.dispatchEvent(new Event('input'));
		}

		await tick();
	};

	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));

	onMount(() => {});
</script>

<div class="m-auto w-full max-w-6xl px-2 @2xl:px-20 translate-y-6 py-24 text-center">
	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t('This chat won’t appear in history and your messages will not be saved.')}
			className="w-full flex justify-center mb-0.5"
			placement="top"
		>
			<div class="flex items-center gap-2 text-gray-500 font-medium text-lg my-2 w-fit">
				<EyeSlash strokeWidth="2.5" className="size-5" />{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<div
		class="w-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4 font-primary"
	>
		<div class="w-full flex flex-col justify-center items-center">
			<div class="flex flex-row justify-center gap-3 @sm:gap-3.5 w-fit px-5">
				<div class="flex shrink-0 justify-center">
					<div class="flex -space-x-4 mb-0.5" in:fade={{ duration: 100 }}>
						{#each models as model, modelIdx}
							<Tooltip
								content={(models[modelIdx]?.info?.meta?.tags ?? [])
									.map((tag) => tag.name.toUpperCase())
									.join(', ')}
								placement="top"
							>
								<button
									on:click={() => {
										selectedModelIdx = modelIdx;
									}}
								>
									<img
										crossorigin="anonymous"
										src={model?.info?.meta?.profile_image_url ??
											($i18n.language === 'dg-DG'
												? `/doge.png`
												: `${WEBUI_BASE_URL}/static/favicon.png`)}
										class=" size-9 @sm:size-10 rounded-full border-[1px] border-gray-100 dark:border-none"
										alt="logo"
										draggable="false"
									/>
								</button>
							</Tooltip>
						{/each}
					</div>
				</div>

				<div class=" text-3xl @sm:text-3xl line-clamp-1" in:fade={{ duration: 100 }}>
					{#if models[selectedModelIdx]?.name}
						{models[selectedModelIdx]?.name}
					{:else}
						안녕하세요, 전북대학교 AI Mentor입니다
					{/if}
				</div>
			</div>

			<div class="flex mt-1 mb-2">
				<div in:fade={{ duration: 100, delay: 50 }}>
					{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
						<Tooltip
							className=" w-fit"
							content={marked.parse(
								sanitizeResponseContent(models[selectedModelIdx]?.info?.meta?.description ?? '')
							)}
							placement="top"
						>
							<div
								class="mt-0.5 px-2 text-sm font-normal text-gray-500 dark:text-gray-400 line-clamp-2 max-w-xl markdown"
							>
								{@html marked.parse(
									sanitizeResponseContent(models[selectedModelIdx]?.info?.meta?.description)
								)}
							</div>
						</Tooltip>

						{#if models[selectedModelIdx]?.info?.meta?.user}
							<div class="mt-0.5 text-sm font-normal text-gray-400 dark:text-gray-500">
								By
								{#if models[selectedModelIdx]?.info?.meta?.user.community}
									<a
										href="https://openwebui.com/m/{models[selectedModelIdx]?.info?.meta?.user
											.username}"
										>{models[selectedModelIdx]?.info?.meta?.user.name
											? models[selectedModelIdx]?.info?.meta?.user.name
											: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}</a
									>
								{:else}
									{models[selectedModelIdx]?.info?.meta?.user.name}
								{/if}
							</div>
						{/if}
					{/if}
				</div>
			</div>

			<div class="text-base font-normal @md:max-w-3xl w-full py-3 {atSelectedModel ? 'mt-2' : ''}">
				<MessageInput
					{history}
					{selectedModels}
					bind:files
					bind:prompt
					bind:autoScroll
					bind:selectedToolIds
					bind:selectedFilterIds
					bind:imageGenerationEnabled
					bind:codeInterpreterEnabled
					bind:webSearchEnabled
					bind:atSelectedModel
					{toolServers}
					{transparentBackground}
					{stopResponse}
					{createMessagePair}
					placeholder={$i18n.t('How can I help you today?')}
					onChange={(input) => {
						if (input.prompt !== null) {
							localStorage.setItem(`chat-input`, JSON.stringify(input));
						} else {
							localStorage.removeItem(`chat-input`);
						}
					}}
					on:upload={(e) => {
						dispatch('upload', e.detail);
					}}
					on:submit={(e) => {
						dispatch('submit', e.detail);
					}}
				/>
			</div>
		</div>
	</div>
	<div class="mx-auto max-w-2xl font-primary mt-2" in:fade={{ duration: 200, delay: 200 }}>
		<div class="mx-5">
			<Suggestions
				suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
					models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
					$config?.default_prompt_suggestions ??
					[
						{
							title: ["커리큘럼 추천", "맞춤형 수업 계획을 제안해드려요"],
							content: "저는 인공지능과 반도체를 융합한 전문가가 되고 싶은데, 어떤 수업들을 들으면 좋을까요?"
						},
						{
							title: ["교수님 검색", "관심 있는 교수님의 연구분야를 찾아드려요"],
							content: "인공지능 관련 연구를 하시는 전북대 교수님은 누구인가요?"
						},
						{
							title: ["학과 정보", "융합학과 및 타학과 커리큘럼을 비교해드려요"],
							content: "컴퓨터인공지능학부는 무슨 학과인가요?"
						},
						{
							title: ["진로 추천", "졸업 후 경로를 분석해드려요"],
							content: "융합학과 복수전공을 마친 후 어떤 진로로 나아갈 수 있을까요?"
						},
						{
							title: ["수업 추천", "관심사 기반으로 강의를 추천해드려요"],
							content: "데이터 과학에 관심이 있는데, 관련된 전북대 수업을 추천해주세요."
						}
					]}
				inputValue={prompt}
				on:select={(e) => {
					selectSuggestionPrompt(e.detail);
				}}
			/>
		</div>
	</div>
</div>
