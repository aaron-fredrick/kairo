<script>
  import { onMount, onDestroy } from 'svelte';
  import Sidebar from './lib/Sidebar.svelte';
  import ChatPanel from './lib/ChatPanel.svelte';
  import { getCookie, setCookie } from './lib/cookies.js';
  import { joinServer, fetchRooms, fetchMessages } from './lib/api.js';

  let rooms = [];
  let selectedRoomId = null;
  let messages = [];
  let tempMessages = [];
  let currentMessage = '';
  let username = 'Guest';
  let token = null;
  let ws = null;

  let isLoadingRooms = true;
  let isLoadingMessages = false;

  let chatPanelRef = null;

  $: allMessages = [...messages, ...tempMessages];

  // ── Session management ──────────────────────────────────────────────────────

  async function resolveSession() {
    token = getCookie('kairo_token');
    username = getCookie('kairo_username') || 'Guest';
    if (!token) await refreshSession();
  }

  async function refreshSession() {
    const data = await joinServer();
    token = data.access_token;
    username = data.username;
    setCookie('kairo_token', token);
    setCookie('kairo_username', username);
  }

  // ── Initialisation ──────────────────────────────────────────────────────────

  async function initialize() {
    isLoadingRooms = true;
    try {
      await resolveSession();

      let roomsRes = await fetchRooms(token);
      if (roomsRes.status === 401) {
        setCookie('kairo_token', '', -1);
        await refreshSession();
        roomsRes = await fetchRooms(token);
      }

      if (roomsRes.ok) {
        rooms = await roomsRes.json();
        const publicRoom = rooms.find(r => r.name === 'public');
        selectRoom(publicRoom ? publicRoom.id : rooms[0]?.id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      isLoadingRooms = false;
    }
  }

  // ── Room selection ──────────────────────────────────────────────────────────

  function selectRoom(roomId) {
    if (!roomId) return;
    selectedRoomId = roomId;
    messages = [];
    tempMessages = [];
    loadMessages(roomId);
    connectWebSocket(roomId);
  }

  // ── Message loading ─────────────────────────────────────────────────────────

  async function loadMessages(roomId) {
    isLoadingMessages = true;
    try {
      const data = await fetchMessages(token, roomId);
      messages = data.map(m => ({
        id: m.id,
        sender: m.sender_username,
        content: m.content,
        time: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        loading: false,
        attachments: m.attachments ?? [],
      }));
      chatPanelRef?.scrollToBottom();
    } catch (e) {
      console.error(e);
    } finally {
      isLoadingMessages = false;
    }
  }

  // ── WebSocket ───────────────────────────────────────────────────────────────

  function connectWebSocket(roomId) {
    if (ws) ws.close();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat/${roomId}?token=${token}`);
    ws.onmessage = handleWebSocketMessage;
  }

  function handleWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);

      if (data.event === 'new_message') {
        reconcileDelivery(data);
        return;
      }

      if (data.event === 'thumbnails_ready') {
        handleThumbnailsReady(data);
        return;
      }
    } catch (e) {
      console.error(e);
    }
  }

  function reconcileDelivery(data) {
    if (data.nonce) {
      tempMessages = tempMessages.filter(m => m.nonce !== data.nonce);
    } else {
      const idx = tempMessages.findIndex(m => m.sender === data.sender && m.content === data.content);
      if (idx !== -1) tempMessages = tempMessages.filter((_, i) => i !== idx);
    }

    if (!messages.find(m => m.id === data.id)) {
      messages = [...messages, {
        id: data.id,
        sender: data.sender,
        content: data.content,
        time: new Date(data.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        loading: false,
        attachments: data.attachments ?? [],
      }];
      chatPanelRef?.scrollToBottom();
    }
  }

  /**
   * Thumbnail generation completed for blob_hash.
   * Patch all messages that reference this blob so their attachment card
   * swaps the spinner for the actual thumbnail image.
   */
  function handleThumbnailsReady(data) {
    const patch = (list) =>
      list.map(m => {
        if (!m.attachments || m.attachments.length === 0) return m;
        const newAttachments = m.attachments.map(att => {
            if (att.blob_hash !== data.hash_id) return att;
            return { ...att, thumbnails: data.thumbnails, thumbnails_ready: true };
        });
        return { ...m, attachments: newAttachments };
      });

    messages = patch(messages);
    tempMessages = patch(tempMessages);
  }

  // ── Sending ─────────────────────────────────────────────────────────────────

  function sendMessage({ detail } = {}) {
    const attachments = detail?.attachments ?? [];
    if (!currentMessage.trim() && attachments.length === 0) return;
    if (!ws) return;

    const nonce = `${Date.now()}-${Math.random()}`;

    tempMessages = [...tempMessages, {
      id: nonce,
      nonce,
      sender: username,
      content: currentMessage,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      loading: true,
      attachments,
    }];
    chatPanelRef?.scrollToBottom();

    ws.send(JSON.stringify({
      content: currentMessage,
      nonce,
      blob_hashes: attachments.map(a => a.blob_hash),
    }));

    currentMessage = '';
  }

  // ── Lifecycle ───────────────────────────────────────────────────────────────

  onMount(initialize);
  onDestroy(() => { if (ws) ws.close(); });
</script>

<main class="app-layout">
  <Sidebar
    {rooms}
    {selectedRoomId}
    {username}
    {isLoadingRooms}
    on:selectRoom={(e) => selectRoom(e.detail)}
  />
  <ChatPanel
    bind:this={chatPanelRef}
    {rooms}
    {selectedRoomId}
    {allMessages}
    {username}
    {isLoadingMessages}
    {token}
    bind:currentMessage
    on:send={sendMessage}
  />
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
  }

  .app-layout {
    display: flex;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }
</style>
