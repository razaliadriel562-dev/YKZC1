// 领用弹窗逻辑
let currentMaterialId = null;

function setClaimMaterial(id, name, stock) {
    currentMaterialId = id;
    document.getElementById('modalMaterialName').textContent = `领取：${name}`;
    document.getElementById('modalMaterialId').value = id;
    document.getElementById('modalMaxStock').textContent = stock;
    document.getElementById('modalAmount').max = stock;
}

document.addEventListener('DOMContentLoaded', function() {
    const claimForm = document.getElementById('claimForm');
    if (claimForm) {
        claimForm.addEventListener('submit', function(e) {
            if (currentMaterialId) {
                this.action = `/claim/${currentMaterialId}`;
            }
        });
    }

    // --- 现代聊天逻辑 ---
    const chatBox = document.getElementById('chat-box');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const currentUserNameElement = document.getElementById('currentUserName');
    const currentUserName = currentUserNameElement ? currentUserNameElement.textContent.trim() : '';

    if (chatBox && chatForm) {
        // 发送消息
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const msg = messageInput.value.trim();
            if (!msg) return;

            fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `message=${encodeURIComponent(msg)}`
            }).then(() => {
                messageInput.value = '';
                loadMessages();
            });
        });

        // 加载消息并区分左右
        function loadMessages() {
            fetch('/get_messages')
                .then(res => res.json())
                .then(messages => {
                    // 判断用户是否正在翻看历史记录（如果在底部则自动滚动，否则不干扰用户）
                    const isScrolledToBottom = chatBox.scrollHeight - chatBox.clientHeight <= chatBox.scrollTop + 50;

                    chatBox.innerHTML = '';
                    messages.forEach(m => {
                        const isMe = m.name === currentUserName;
                        const div = document.createElement('div');

                        // flex 布局推左或推右
                        div.className = `d-flex w-100 ${isMe ? 'justify-content-end' : 'justify-content-start'}`;

                        const adminBadge = m.is_admin ? '<span class="badge bg-warning text-dark ms-2" style="font-size:0.65rem; padding: 3px 6px;">管理员</span>' : '';

                        // 动态组装 HTML
                        div.innerHTML = `
                            <div class="chat-bubble ${isMe ? 'chat-bubble-me' : 'chat-bubble-other'}">
                                <div class="chat-bubble-header d-flex align-items-end mb-1 ${isMe ? 'justify-content-end' : ''}">
                                    <span class="chat-name fw-bold" style="font-size: 0.8rem; opacity: 0.9;">${isMe ? '我' : m.name}</span>
                                    ${adminBadge}
                                    <span class="chat-time ms-2" style="font-size: 0.7rem; opacity: 0.5;">${m.time}</span>
                                </div>
                                <div class="chat-bubble-text text-break" style="font-size: 1rem; line-height: 1.5;">
                                    ${m.message}
                                </div>
                            </div>
                        `;
                        chatBox.appendChild(div);
                    });

                    if (isScrolledToBottom) {
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }
                });
        }

        loadMessages();
        setInterval(loadMessages, 2000);
    }
});