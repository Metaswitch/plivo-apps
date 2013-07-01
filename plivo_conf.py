from flask import Flask, request, make_response
import plivo
import os

SERVER_NAME = '127.0.0.1:5000'

app = Flask(__name__)

@app.route('/answered/', methods=['GET', 'POST'])
def confselect():
    response = plivo.Response()
    getdigits = response.addGetDigits(
        action='http://' + SERVER_NAME + '/confroom/',
        timeout='15',
        finishOnKey='#',
        method='GET'
    )
    getdigits.addWait(length='1')
    getdigits.addSpeak('Please enter your conference i d, followed by the pound key.')
    response.addSpeak(body="Input not received. Thank you.")
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route('/confroom/', methods=['GET', 'POST'])
def confroom():
    if request.method == 'GET':
        conf = request.args.get('Digits', '')
    elif request.method == 'POST':
        conf = request.form.get('Digits', '')

    response = plivo.Response()
    response.addSpeak(body="Now entering conference " + ",".join(list(str(conf))))
    response.addConference(
        enterSound='beep:2',
        exitSound='beep:1',
        waitSound='http://' + SERVER_NAME + '/confwait/',
        body=conf
    )

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

@app.route('/confwait/', methods=['POST'])
def confwait():
    response = plivo.Response()
    # response.addSpeak(body='You are the first participant')
    response.addPlay(body='http://localhost/music.mp3')
    # response.addWait(length='10')

    print response.to_xml()
    xml_response = make_response(response.to_xml())
    xml_response.headers["Content-type"] = "text/xml"
    return xml_response

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    app.run(host='0.0.0.0', port=5000)
