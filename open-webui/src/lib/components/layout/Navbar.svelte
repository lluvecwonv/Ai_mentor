<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		WEBUI_NAME,
		chatId,
		mobile,
		settings,
		showArchivedChats,
		showControls,
		showSidebar,
		temporaryChatEnabled,
		user
	} from '$lib/stores';

	import { slide } from 'svelte/transition';
	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Menu from './Navbar/Menu.svelte';
	import { page } from '$app/stores';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';
	import Map from '../icons/Map.svelte';
	import { stringify } from 'postcss';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Plus from '../icons/Plus.svelte';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let chat;
	export let selectedModels;
	export let showModelSelector = true;

	let showShareChatModal = false;
	let showDownloadChatModal = false;
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />

<div class="sticky top-0 z-30 w-full px-1.5 py-1.5 -mb-8 flex items-center">
	<div
		class=" bg-linear-to-b via-50% from-white via-white to-transparent dark:from-gray-900 dark:via-gray-900 dark:to-transparent pointer-events-none absolute inset-0 -bottom-7 z-[-1]"
	></div>

	<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
		<div class="flex items-center w-full max-w-full gap-2">
			<!-- AI 멘토: 새 채팅 버튼 -->
			<div class="flex flex-none items-center">
				<Tooltip content="새 채팅">
					<button
						id="new-chat-button"
						class="flex cursor-pointer px-3 py-2 rounded-xl bg-blue-500 text-white hover:bg-blue-600 transition shadow-md"
						on:click={() => {
							window.location.href = '/';
						}}
						aria-label="New Chat"
					>
						<div class="m-auto self-center">
							<Plus className="size-5" strokeWidth="2.5" />
						</div>
					</button>
				</Tooltip>
			</div>

			<!-- AI 멘토: 사이드바 토글 버튼 제거 -->

			<div
				class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
			>
				{#if showModelSelector}
					<ModelSelector bind:selectedModels showSetDefault={!shareEnabled} />
				{/if}
			</div>

		</div>
	</div>
</div>
