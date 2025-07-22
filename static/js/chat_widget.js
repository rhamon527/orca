const socket = io();
const bubble = document.getElementById('chat-bubble');
const panel = document.getElementById('chat-panel');
const widgetMsgs = document.getElementById('widget-msgs');
const widgetInput = document.getElementById('widget-input');
const onlineCount = document.getElementById('online-count');

socket.on('user_list', users => {
  onlineCount.textContent = users.length;
});

socket.on('new_message', data => {
  const li = document.createElement('li');
  li.textContent = `${data.user}: ${data.msg}`;
  widgetMsgs.appendChild(li);
  widgetMsgs.scrollTop = widgetMsgs.scrollHeight;
});

bubble.addEventListener('click', () => {
  panel.classList.toggle('hidden');
});

widgetInput.addEventListener('keypress', e => {
  if (e.key === 'Enter' && widgetInput.value.trim()) {
    socket.emit('send_message', { msg: widgetInput.value });
    widgetInput.value = '';
  }
});
