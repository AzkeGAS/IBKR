from flask import Flask, request
import config
from DAX import TestApp

webhook = Flask(__name__)
@webhook.route("/", methods=['POST'])

def alerta():
  config.msg = request.json
  # Safety layer
  if config.msg.get('password')!=config.PASSWORD:
      return {'code':'error',
              'message':'User not authorized'}
  print(config.msg)

  app = TestApp()
  app.connect("127.0.0.1", 7497, 100)
  app.run()

  return {
      'code': 'Success',
      'msg':config.msg,
  }

if __name__ == "__main__":
  webhook.run(host='127.0.0.1', port=80, debug=True)

