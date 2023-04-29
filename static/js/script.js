


var socket = io();
function runScript() {
    var params = {
        aws_access_key_id: document.getElementById("aws_access_key_id").value,
        aws_secret_access_key: document.getElementById("aws_secret_access_key").value,
        region: document.getElementById("region").value
    };
    socket.emit('run_script', params);
}
socket.on('output', function (data) {
    var outputDiv = document.getElementById("output");
    outputDiv.innerHTML += data + "<br>";
});