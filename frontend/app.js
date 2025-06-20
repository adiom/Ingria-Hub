let ws = new WebSocket(`ws://${location.host}/ws/stream_gemini`);

ws.onmessage = function(event) {
  const output = document.getElementById('output');
  if (event.data === '[END]') {
    output.innerHTML += '<hr/>';
    return;
  }
  output.innerHTML += event.data;
};

function sendMessage() {
  const input = document.getElementById('input');
  ws.send(input.value);
  input.value = '';
} 