from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from create_dotp import run, test_run
from utils.functions_login import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('run_script')
def handle_run_script(script_params):
    # Run the Python script and emit the output to the client as it is generated
    # Use the emit function to send the output to the client
    # The 'output' event name can be customized

    if script_params["project"] == '':
        emit('output', 'Using default project name "dev-ops-tools-pack"')
        script_params["project"] = "dev-ops-tools-pack"

    if script_params["region"] == '':
        emit('output', 'Using default region "eu-central-1"')
        script_params["region"] = "eu-central-1"
    
    if script_params["multiple_vm"] == True:
        emit('output', f'You have opted for multiple virtual machines')
    else:
        emit('output', f'You have opted for single virtual machine')
    
    if script_params["aws_access_key_id"] == '' or script_params["aws_secret_access_key"] == '':
        emit('output', "[error] AWS Secret Key ID or AWS Secret Access Key is missing!")
        return
    
    login(aws_access_key_id=script_params["aws_access_key_id"], 
          aws_secret_access_key=script_params["aws_secret_access_key"], 
          region=script_params["region"])
    
    # test_run(project=script_params["project"], 
    #                             aws_access_key_id=script_params["aws_access_key_id"], 
    #                             aws_secret_access_key=script_params["aws_secret_access_key"], 
    ##                             region=script_params["region"],
    #                             multiple_vms = script_params["multiple_vm"])
    
    run(multiple_vms = script_params["multiple_vm"], project=script_params["project"], _instance_type=script_params["instance_type"])



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5555, debug=True)
