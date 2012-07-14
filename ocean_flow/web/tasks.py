'''
Created on Jul 10, 2012

@author: sean
'''
from ocean_flow.gdal2tiles import GlobalMercator
from ocean_flow.get_data import download_noaa_data
from ocean_flow.tiler import Tiler
import netCDF4
import PIL.Image
from StringIO import StringIO
from os.path import join


_CACHE_ = None
_TILER_ = None

def _get_mc():
    global _CACHE_
    
    if _CACHE_ is None:
        print "mc_ is None"
        import pylibmc
        _CACHE_ = pylibmc.Client(["127.0.0.1"], binary=True)
    return _CACHE_


def _get_tiler():
    global _TILER_
    
    if _TILER_ is None:
        print "tiler"
        
        mc_ = _get_mc()
        proj_type = GlobalMercator
        data = netCDF4.Dataset(mc_['app:nc_file'])
        lats = data.variables['lat']
        lons = data.variables['lon']
        _TILER_ = Tiler(proj_type, data, lats, lons)
        
    return _TILER_

def download_and_cache_filename():
    
    mc_ = _get_mc()
        
    mc_['app:nc_file'] = '..working..'
    filename = download_noaa_data()
    mc_['app:nc_file'] = filename



def cache_tile_data(tx, ty, zoom, tile_size, sub_sample):
    
    mc_ = _get_mc()
    tiler = _get_tiler()

    size = (tile_size / sub_sample)
    zoom_dir = join('%spx' % (size,), str(zoom))
    cache_name = join(zoom_dir, '%sx_%sy' % (tx, ty))
    
    data_cache_key = cache_name + '.numpy'
    
    if data_cache_key not in mc_:
        data_x, data_y = tiler.get_tile(tx, ty, zoom, tile_size, sub_sample)
        data_x = data_x.astype('float32')
        data_y = data_y.astype('float32')

        mc_[data_cache_key] = data_x, data_y  
    else:
        data_x, data_y = mc_[cache_name + '.numpy']
    
    return dict(u=data_x.tolist(), v=data_y.tolist())

def make_image(data_u, data_v, tx, ty, zoom, tile_size, sub_sample):
    tiler = _get_tiler()
    rgba = tiler.rgba(data_u, data_v, tile_size)
    image = PIL.Image.fromarray(rgba)
    image = image.resize([tile_size, tile_size])
    
    output = StringIO()
    image.save(output, format='jpeg')
    contents = output.getvalue()
    output.close()
    
    return contents

def cache_image(tx, ty, zoom, tile_size, sub_sample):

    size = (tile_size / sub_sample)
    zoom_dir = join('%spx' % (size,), str(zoom))
    cache_name = join(zoom_dir, '%sx_%sy' % (tx, ty))
    
    mc_ = _get_mc()
    tiler = _get_tiler()

    data_cache_key = cache_name + '.numpy'
    image_cache_key = cache_name + '.jpeg'
    if image_cache_key in mc_:
        return mc_[image_cache_key]
    
    if data_cache_key in mc_:
        data_x, data_y = mc_[data_cache_key] 
    else:
        data_x, data_y = tiler.get_tile(tx, ty, zoom, tile_size, sub_sample)
        data_x = data_x.astype('float32')
        data_y = data_y.astype('float32')
    
        mc_[data_cache_key] = data_x, data_y
    
    image_buffer = make_image(data_x, data_y, tx, ty, zoom, tile_size, sub_sample)
    mc_[image_cache_key] = image_buffer
        
    return image_buffer



    