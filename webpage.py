import os
from flask import Flask, render_template, redirect, url_for, request

registered = []
file_name = './data/registered.dat'
try:
    f=open(file_name, 'r')
    for r in f:
        registered.append(r[:-1])
    f.close()
except:
    # file doesn't exist create it
    f=open(file_name, 'x')
    f.close()

app = Flask(__name__)

@app.route('/')
def intro():
    return render_template('index.html')

@app.route('/admin/', methods=["POST", "GET"])
def admin():
    if request.method == "POST":
        action = request.form["action"]
        addr = request.form["addr"]

        if action == 'r':
            if not addr in registered:
                registered.append(addr)
        elif action == 'd':
            if addr in registered:
                registered.remove(addr)

        f=open(file_name, 'w')
        for r in registered:
            f.write(r+'\n')
        f.close()
    return render_template('admin.html')

@app.route('/client/', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        addr = request.form["addr"]
        if addr in registered:
            index = registered.index(addr)
            return redirect(url_for("client", id=index))
        else:
            return render_template('login.html')
    elif request.method == "GET":
        return render_template('login.html')

@app.route('/client/<id>/', methods=["POST", "GET"])
def client(id):
    if request.method == "POST":
        type = request.form["type"]
        asset = request.form["asset"]
        price = request.form["price"]
        volume = request.form["volume"]
        mes = request.form["mes"]

        # save order
        order_string = "{},{},{},{},{}".format(type, asset, price, volume, mes)
        file_name = './data/client_order_'+id+'.dat'

        f=open(file_name, 'w')
        f.write(order_string)
        f.close()

    return render_template('client.html')

if __name__ == '__main__':
    app.run(debug=True)
