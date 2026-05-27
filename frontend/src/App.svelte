<script>
  import { onMount, onDestroy } from 'svelte';

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
  
  $: allMessages = [...messages, ...tempMessages];
  
  let chatHistoryRef = null;

  function scrollToBottom() {
    if (chatHistoryRef) {
      setTimeout(() => {
        chatHistoryRef.scrollTop = chatHistoryRef.scrollHeight;
      }, 50);
    }
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  function setCookie(name, value, days = 7) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/`;
  }

  async function joinServer() {
    const joinRes = await fetch('/api/v1/auth/join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (!joinRes.ok) throw new Error('Failed to join server');
    const joinData = await joinRes.json();
    token = joinData.access_token;
    username = joinData.username;
    setCookie('kairo_token', token);
    setCookie('kairo_username', username);
  }

  async function initialize() {
    isLoadingRooms = true;
    try {
      token = getCookie('kairo_token');
      username = getCookie('kairo_username') || 'Guest';

      if (!token) {
        await joinServer();
      }

      let roomsRes = await fetch('/api/v1/rooms', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (roomsRes.status === 401) {
        setCookie('kairo_token', '', -1);
        await joinServer();
        roomsRes = await fetch('/api/v1/rooms', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }

      if (roomsRes.ok) {
        rooms = await roomsRes.json();
        const publicRoom = rooms.find(r => r.name === 'public');
        if (publicRoom) {
          selectRoom(publicRoom.id);
        } else if (rooms.length > 0) {
          selectRoom(rooms[0].id);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      isLoadingRooms = false;
    }
  }

  async function loadRoomMessages(roomId) {
    isLoadingMessages = true;
    messages = [];
    try {
      const res = await fetch(`/api/v1/rooms/${roomId}/messages`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        messages = data.map(m => ({
          id: m.id,
          sender: m.sender_username,
          content: m.content,
          time: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          loading: false
        }));
        scrollToBottom();
      }
    } catch (e) {
      console.error(e);
    } finally {
      isLoadingMessages = false;
    }
  }

  function connectWebSocket(roomId) {
    if (ws) ws.close();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${roomId}?token=${token}`;
    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "new_message") {
          // Remove temp message if it matches our nonce or fallback
          if (data.nonce) {
             tempMessages = tempMessages.filter(m => m.nonce !== data.nonce);
          } else {
             const index = tempMessages.findIndex(m => m.sender === data.sender && m.content === data.content);
             if (index !== -1) {
                 tempMessages.splice(index, 1);
                 tempMessages = [...tempMessages];
             }
          }

          // Ensure no duplicate messages
          if (!messages.find(m => m.id === data.id)) {
            messages = [...messages, {
              id: data.id,
              sender: data.sender,
              content: data.content,
              time: new Date(data.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              loading: false
            }];
            scrollToBottom();
          }
        }
      } catch (e) {
        console.error(e);
      }
    };
  }

  function selectRoom(roomId) {
    selectedRoomId = roomId;
    messages = [];
    tempMessages = [];
    loadRoomMessages(roomId);
    connectWebSocket(roomId);
  }

  function sendMessage() {
    if (!currentMessage.trim() || !ws) return;
    
    const nonce = Date.now().toString() + Math.random().toString();
    
    // Add temp message to UI
    tempMessages = [...tempMessages, {
      id: nonce,
      nonce: nonce,
      sender: username,
      content: currentMessage,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      loading: true
    }];
    scrollToBottom();

    ws.send(JSON.stringify({
      content: currentMessage,
      nonce: nonce
    }));
    
    currentMessage = '';
  }

  onMount(() => {
    initialize();
  });
  
  onDestroy(() => {
    if (ws) ws.close();
  });
</script>

<main class="app-layout">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">⚡</span>
        <h1>KAIRO</h1>
      </div>
    </div>
    
    <div class="section-title">CHANNELS</div>
    <nav class="room-list">
      {#if isLoadingRooms}
        <div class="skeleton-room skeleton"></div>
        <div class="skeleton-room skeleton"></div>
        <div class="skeleton-room skeleton"></div>
      {:else}
        {#each rooms as room}
          <button 
            class="room-item" 
            class:active={room.id === selectedRoomId}
            onclick={() => selectRoom(room.id)}
          >
            <span class="hash">#</span>
            <span class="room-name">{room.name}</span>
          </button>
        {/each}
      {/if}
    </nav>

    <div class="user-profile">
      <div class="avatar">
        <span class="avatar-text">{username.slice(0, 2).toUpperCase()}</span>
        <span class="status-indicator online"></span>
      </div>
      <div class="user-info">
        <span class="username">{username}</span>
        <span class="user-role">Guest User</span>
      </div>
    </div>
  </aside>

  <!-- Chat Area -->
  <section class="chat-container">
    <header class="chat-header">
      <div class="room-title">
        <h2>#{rooms.find(r => r.id === selectedRoomId)?.name || '...'}</h2>
        <p class="room-description">{rooms.find(r => r.id === selectedRoomId)?.description || ''}</p>
      </div>
      <div class="connection-status">
        <span class="status-dot"></span>
        Connected
      </div>
    </header>

    <div class="message-history" bind:this={chatHistoryRef}>
      {#if isLoadingMessages}
        <div class="skeleton-message">
          <div class="skeleton-avatar skeleton"></div>
          <div class="skeleton-content">
             <div class="skeleton-meta skeleton"></div>
             <div class="skeleton-text skeleton"></div>
             <div class="skeleton-text short skeleton"></div>
          </div>
        </div>
        <div class="skeleton-message">
          <div class="skeleton-avatar skeleton"></div>
          <div class="skeleton-content">
             <div class="skeleton-meta skeleton"></div>
             <div class="skeleton-text skeleton"></div>
          </div>
        </div>
      {:else}
        {#each allMessages as message}
          <div class="message-card" class:self={message.sender === username}>
            {#if message.sender !== username}
              <div class="message-avatar">
                {message.sender.slice(0, 2).toUpperCase()}
              </div>
            {/if}
            <div class="message-content-wrapper">
              {#if message.sender === username}
                <div class="message-meta self-meta">
                  <span class="message-time">{message.time}</span>
                  {#if message.loading}
                     <span class="message-status">
                        <span class="loading-icon">⏳</span> Delivering...
                     </span>
                  {/if}
                </div>
              {:else}
                <div class="message-meta">
                  <span class="message-sender">{message.sender}</span>
                  <span class="message-time">{message.time}</span>
                </div>
              {/if}
              <p class="message-text" class:pending={message.loading}>{message.content}</p>
            </div>
          </div>
        {/each}
      {/if}
    </div>

    <form class="message-input-form" onsubmit={(e) => { e.preventDefault(); sendMessage(); }}>
      <button type="button" class="attachment-btn" title="Upload File">
        📎
      </button>
      <textarea 
        bind:value={currentMessage} 
        placeholder="Message #{rooms.find(r => r.id === selectedRoomId)?.name || '...'}..." 
        rows="1"
        onkeydown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
          }
        }}
      ></textarea>
      <button type="submit" class="send-btn" disabled={!currentMessage.trim()}>Send</button>
    </form>
  </section>
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

  /* Sidebar styling */
  .sidebar {
    width: 260px;
    background-color: #252526;
    border-right: 1px solid #333333;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  .sidebar-header {
    padding: 1.5rem;
    border-bottom: 1px solid #333333;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .logo-icon {
    font-size: 1.5rem;
    background: #007acc;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    color: #ffffff;
  }

  .logo h1 {
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    margin: 0;
    color: #cccccc;
  }

  .section-title {
    padding: 1.5rem 1.5rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 700;
    color: #4b5563;
    letter-spacing: 0.1em;
  }

  .room-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .room-item {
    background: transparent;
    border: none;
    outline: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    color: #9ca3af;
    border-radius: 8px;
    text-align: left;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .room-item:hover {
    background-color: #2a2d2e;
    color: #cccccc;
  }

  .room-item.active {
    background-color: #37373d;
    color: #ffffff;
    font-weight: 600;
  }

  .hash {
    color: #858585;
    font-weight: 400;
  }

  .room-item.active .hash {
    color: #007acc;
  }

  .user-profile {
    padding: 1rem;
    background-color: #252526;
    border-top: 1px solid #333333;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .avatar {
    position: relative;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #007acc;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 0.9rem;
    color: white;
  }

  .avatar-text {
    letter-spacing: 0.05em;
  }

  .status-indicator {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid #0f172a;
  }

  .status-indicator.online {
    background-color: #10b981;
  }

  .user-info {
    display: flex;
    flex-direction: column;
  }

  .username {
    font-size: 0.9rem;
    font-weight: 600;
    color: #f3f4f6;
  }

  .user-role {
    font-size: 0.75rem;
    color: #6b7280;
  }

  /* Chat Container */
  .chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #1e1e1e;
  }

  .chat-header {
    height: 70px;
    padding: 0 1.5rem;
    border-bottom: 1px solid #333333;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .room-title h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
  }

  .room-description {
    margin: 0.2rem 0 0;
    font-size: 0.8rem;
    color: #6b7280;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #10b981;
    font-weight: 500;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .message-history {
    flex: 1;
    padding: 1.5rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .message-card {
    display: flex;
    gap: 1rem;
    max-width: 80%;
  }

  .message-card.self {
    align-self: flex-end;
  }

  .message-card.self .message-content-wrapper {
    align-items: flex-end;
  }

  .message-card.self .message-text {
    text-align: right;
  }

  .message-meta.self-meta {
    justify-content: flex-end;
  }

  .message-avatar {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    background: #3c3c3c;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.85rem;
    color: #cccccc;
    flex-shrink: 0;
  }

  .message-content-wrapper {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .message-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .message-sender {
    font-size: 0.85rem;
    font-weight: 600;
    color: #e5e7eb;
  }

  .message-time {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .message-text {
    margin: 0;
    font-size: 0.95rem;
    color: #d1d5db;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  /* Form */
  .message-input-form {
    padding: 1.5rem;
    display: flex;
    gap: 0.75rem;
    border-top: 1px solid #333333;
  }

  .message-input-form textarea {
    flex: 1;
    background-color: #3c3c3c;
    border: 1px solid #3c3c3c;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    color: #cccccc;
    font-size: 0.95rem;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s ease;
    resize: none;
    max-height: 120px;
    overflow-y: auto;
  }

  .message-input-form textarea:focus {
    border-color: #007acc;
  }

  .attachment-btn {
    background: transparent;
    border: 1px solid #1f2937;
    color: #9ca3af;
    border-radius: 8px;
    padding: 0 1rem;
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .attachment-btn:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #f3f4f6;
  }

  .message-input-form .send-btn {
    background: #007acc;
    color: white;
    border: none;
    outline: none;
    border-radius: 8px;
    padding: 0 1.5rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .message-input-form .send-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .message-input-form .send-btn:disabled {
    background: #1f2937;
    color: #4b5563;
    cursor: not-allowed;
  }

  .message-attachment {
    margin-top: 0.75rem;
  }

  .image-placeholder {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background-color: #111827;
    border: 1px dashed #374151;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    color: #9ca3af;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .image-placeholder:hover {
    border-color: #6366f1;
    color: #e5e7eb;
  }

  .message-status {
    font-size: 0.75rem;
    color: #f59e0b;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-weight: 500;
  }
  .loading-icon {
    font-size: 0.8rem;
    animation: spin 2s linear infinite;
  }
  @keyframes spin {
    100% { transform: rotate(360deg); }
  }
  .message-text.pending {
    opacity: 0.6;
  }
  
  @keyframes shimmer {
    0% { background-position: -400px 0; }
    100% { background-position: 400px 0; }
  }

  .skeleton {
    background: #333333;
    background-image: linear-gradient(90deg, #333333 0px, #3c3c3c 40px, #333333 80px);
    background-size: 800px 100%;
    animation: shimmer 2s infinite linear;
  }

  .skeleton-room {
    height: 38px;
    margin-bottom: 8px;
    border-radius: 8px;
  }

  .skeleton-message {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.25rem;
  }

  .skeleton-avatar {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  .skeleton-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .skeleton-meta {
    height: 14px;
    width: 120px;
    border-radius: 4px;
  }

  .skeleton-text {
    height: 16px;
    width: 80%;
    border-radius: 4px;
  }
  
  .skeleton-text.short {
    width: 50%;
  }
</style>
