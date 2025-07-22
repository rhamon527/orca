const socket = io();
const msgs = document.getElementById('msgs');
const input = document.getElementById('input-msg');

socket.on('user_list', users=>{
  // opcional: exibir lista de online
});

socket.on('new_message', data=>{
  const li = document.createElement('li');
  li.textContent = `${data.user}: ${data.msg}`;
  msgs.appendChild(li);
});

input.addEventListener('keypress', e=>{
  if(e.key === 'Enter' && input.value.trim()){
    socket.emit('send_message', {msg: input.value});
    input.value = '';
  }
});
