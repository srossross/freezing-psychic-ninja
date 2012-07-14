from argparse import ArgumentParser
from flask import Flask, jsonify, render_template, request, make_response, Response
from ocean_flow.web.tasks import download_and_cache_filename, cache_tile_data, \
    cache_image
from rq import Queue
from worker import conn
import pylibmc
import os

queue = Queue(connection=conn)
mc = pylibmc.Client(["127.0.0.1"], binary=True)

app = Flask(__name__)

def get_data_file():
    
    nc_file = mc.get('app:nc_file')
    if nc_file is None:        
        job = queue.enqueue(download_and_cache_filename)
        return False, dict(job_id=job.id, status='submitted')
    elif nc_file == '..working..':
        return False, dict(status='working')
    else:
        return True, dict(status='ok')
    

#def get_tile_data(tx, ty, zoom, tile_size, sub_sample):
#    
#    from os.path import join
#    
#    size = (tile_size / sub_sample)
#    zoom_dir = join('%spx' % (size,), str(zoom))
#    
#    cache_name = join(zoom_dir, '%sx_%sy' % (tx, ty))
#    
#    get_tile_data_cache(cache_name, tx, ty, zoom, tile_size, sub_sample)
#        
#    u, v = mc[cache_name]
#    return True, dict(status='ok', u=u.tolist(), v=v.tolist())


@app.route("/tile.jpeg")
def tile_image():
    tx = int(request.args.get('x', None))
    ty = int(request.args.get('y', None))
    zoom = int(request.args.get('zoom', None))
    tile_size = int(request.args.get('size', None))
    sub_sample = int(request.args.get('sub_sample', default=1))
    
    def wsgi_app(environ, start_response):
        jepg_data = cache_image(tx, ty, zoom, tile_size, sub_sample)
        start_response('200 OK', [('Content-type', 'image/jpeg')])
        return jepg_data 

    return make_response(wsgi_app)


@app.route("/tile.json")
def tile_json():
    tx = int(request.args.get('x', None))
    ty = int(request.args.get('y', None))
    zoom = int(request.args.get('zoom', None))
    tile_size = int(request.args.get('size', None))
    sub_sample = int(request.args.get('sub_sample', default=1))
    
    data = cache_tile_data(tx, ty, zoom, tile_size, sub_sample)
    
    response = jsonify(name="tile-server", version="0-dev", **data)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'X-Request, X-Requested-With'
    
    return response

@app.route("/ready.json")
def hello_server():
    have_file, status = get_data_file()
    response = jsonify(name="tile-server", version="0-dev", **status)

    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'X-Request, X-Requested-With'

    return response

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    parser.add_argument('-p', '--port', default=port, type=int)
    parser.add_argument('-d', '--debug', default=False, action='store_const', const=True)
    
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)

