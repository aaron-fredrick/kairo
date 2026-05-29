<script>
  import { onMount, onDestroy } from 'svelte';
  import Sidebar from './lib/Sidebar.svelte';
  import ChatPanel from './lib/ChatPanel.svelte';
  import { getCookie } from './lib/cookies.js';
  import { joinServer, fetchRooms, fetchMessages, fetchUserProfile, fetchPresence } from './lib/api.js';

  let rooms = [];
  let selectedRoomId = null;
  let messages = [];
  let tempMessages = [];
  let currentMessage = '';
  let username = 'Guest';
  let userRole = 'normal';
  let userPfpUrls = null;
  let token = null;
  let ws = null;
  let activeUsers = [];
  let pingInterval = null;

  let isLoadingRooms = true;
  let isLoadingMessages = false;

  let chatPanelRef = null;

  $: allMessages = [...messages, ...tempMessages];

  // ── Session management ──────────────────────────────────────────────────────

  /**
   * Called by the API client whenever a silent re-join occurs.
   * Keeps local state and WS token in sync without a page reload.
   */
  function onTokenRefreshed(newToken, newUsername) {
    token = newToken;
    username = newUsername;
  }

  async function resolveSession() {
    token = getCookie('kairo_token');
    username = getCookie('kairo_username') || 'Guest';
    if (!token) {
      const data = await joinServer(onTokenRefreshed);
      token = data.access_token;
      username = data.username;
    }
  }

  // ── Initialisation ──────────────────────────────────────────────────────────

  async function initialize() {
    isLoadingRooms = true;
    try {
      await resolveSession();

      const roomsRes = await fetchRooms(onTokenRefreshed);
      if (!roomsRes.ok) throw new Error(`Failed to load rooms (${roomsRes.status})`);
      rooms = await roomsRes.json();

      try {
        const profile = await fetchUserProfile(onTokenRefreshed);
        userPfpUrls = profile.pfp_urls;
        userRole = profile.role;
      } catch (e) {
        console.warn('Could not fetch user profile', e);
      }

      const publicRoom = rooms.find(r => r.name === 'public');
      selectRoom(publicRoom ? publicRoom.id : rooms[0]?.id);
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
    activeUsers = [];
    loadMessages(roomId);
    connectWebSocket(roomId);
  }

  // ── Message loading ─────────────────────────────────────────────────────────

  async function loadMessages(roomId) {
    isLoadingMessages = true;
    try {
      const data = await fetchMessages(roomId, onTokenRefreshed);
      messages = data.map(m => ({
        id: m.id,
        sender: m.sender_username,
        sender_pfp_urls: m.sender_pfp_urls,
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

  async function loadPresence(roomId) {
    try {
      const res = await fetchPresence(roomId, onTokenRefreshed);
      if (res.ok) {
        const data = await res.json();
        activeUsers = data.users;
      }
    } catch (e) {
      console.error('Failed to load presence', e);
    }
  }

  // ── WebSocket ───────────────────────────────────────────────────────────────

  function connectWebSocket(roomId) {
    if (ws) ws.close();
    if (pingInterval) clearInterval(pingInterval);
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Always read token at connection time so a refreshed token is used
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat/${roomId}?token=${getCookie('kairo_token')}`);
    ws.onmessage = handleWebSocketMessage;
    ws.onopen = () => loadPresence(roomId);

    pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ event: 'ping' }));
      }
    }, 30000);
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
      
      if (data.event === 'pfp_updated') {
        if (data.username === username) {
          userPfpUrls = data.pfp_urls;
        }
        // Patch messages where sender === data.username
        const patch = (list) => list.map(m => {
          if (m.sender === data.username || m.sender_username === data.username) {
            return { ...m, sender_pfp_urls: data.pfp_urls };
          }
          return m;
        });
        messages = patch(messages);
        tempMessages = patch(tempMessages);
        
        activeUsers = activeUsers.map(u => u.username === data.username ? { ...u, pfp_urls: data.pfp_urls } : u);
        return;
      }

      if (data.event === 'presence_update') {
        if (data.action === 'join') {
          if (!activeUsers.find(u => u.username === data.username)) {
            activeUsers = [...activeUsers, {
              username: data.username,
              role: data.role,
              pfp_urls: data.pfp_urls
            }];
          }
        } else if (data.action === 'leave') {
          activeUsers = activeUsers.filter(u => u.username !== data.username);
        }
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
        sender_pfp_urls: data.sender_pfp_urls,
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
      sender_pfp_urls: userPfpUrls,
      content: currentMessage,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      loading: true,
      attachments,
    }];
    chatPanelRef?.scrollToBottom();

    ws.send(JSON.stringify({
      content: currentMessage,
      nonce,
      attachments: attachments.map(a => ({
        upload_id: a.upload_id,
        filename: a.filename,
        mime_type: a.mime_type,
        size_bytes: a.size_bytes
      })),
    }));

    currentMessage = '';
  }

  // ── Lifecycle ───────────────────────────────────────────────────────────────

  onMount(initialize);
  onDestroy(() => { 
    if (ws) ws.close(); 
    if (pingInterval) clearInterval(pingInterval);
  });
</script>

<main class="app-layout">
  <Sidebar
    {rooms}
    {selectedRoomId}
    {username}
    {userRole}
    {userPfpUrls}
    {token}
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
    {activeUsers}
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
