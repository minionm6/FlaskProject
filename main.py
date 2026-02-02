from flask import Flask
from flask import render_template

app = Flask(__name__)


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/p2')
def greet():
    return render_template('p2.html')





if __name__ == '__main__':
    app.run(debug = True)
