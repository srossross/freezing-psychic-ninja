
import netCDF4
from argparse import ArgumentParser
import gdal2tiles
import numpy as np
from scipy.interpolate import griddata
from scipy.interpolate import LinearNDInterpolator
import json

def hsv_to_rgb(hsv):
    """
    convert hsv values in a numpy array to rgb values
    both input and output arrays have shape (M,N,3)
    """
    h = hsv[:,:,0]; s = hsv[:,:,1]; v = hsv[:,:,2]
    r = np.empty_like(h); g = np.empty_like(h); b = np.empty_like(h)
    i = (h*6.0).astype(np.int)
    f = (h*6.0) - i
    p = v*(1.0 - s)
    q = v*(1.0 - s*f)
    t = v*(1.0 - s*(1.0-f))
    idx = i%6 == 0
    r[idx] = v[idx]; g[idx] = t[idx]; b[idx] = p[idx]
    idx = i == 1
    r[idx] = q[idx]; g[idx] = v[idx]; b[idx] = p[idx]
    idx = i == 2
    r[idx] = p[idx]; g[idx] = v[idx]; b[idx] = t[idx]
    idx = i == 3
    r[idx] = p[idx]; g[idx] = q[idx]; b[idx] = v[idx]
    idx = i == 4
    r[idx] = t[idx]; g[idx] = p[idx]; b[idx] = v[idx]
    idx = i == 5
    r[idx] = v[idx]; g[idx] = p[idx]; b[idx] = q[idx]
    idx = s == 0
    r[idx] = v[idx]; g[idx] = v[idx]; b[idx] = v[idx]
    rgb = np.empty_like(hsv)
    rgb[:,:,0]=r; rgb[:,:,1]=g; rgb[:,:,2]=b
    return rgb

class Tiler(object):
    def __init__(self, proj_type, data, lats, lons):
        self.proj_type = proj_type
        self.lats = lats
        self.lons = lons
        self.data = data
        self.lon_bounds = [np.min(self.lons), np.max(self.lons)]
        self.lat_bounds = [np.min(self.lats), np.max(self.lats)]
        self.u = self.data.variables['u'][-1, 0, :, :]
        self.v = self.data.variables['v'][-1, 0, :, :]
        
        self.mask = np.zeros(self.u.shape, dtype=bool)
        self.mask[np.isnan(self.u) | np.isnan(self.v)] = 1
        
        self.u[self.mask] = 0
        self.v[self.mask] = 0
        
        points_x, points_y = np.meshgrid(self.lons, self.lats)
        self.u_interp = LinearNDInterpolator((points_x.flat, points_y.flat), self.u.flat, fill_value=0)
        self.v_interp = LinearNDInterpolator((points_x.flat, points_y.flat), self.v.flat, fill_value=0)
        self.mask_interp = LinearNDInterpolator((points_x.flat, points_y.flat), self.mask.flat, fill_value=0)
        

    def get_tile(self, tx, ty, zoom, tile_size, sub_sample):
        
        proj = self.proj_type(tile_size)
        min_lat, min_lon, max_lat, max_lon = proj.TileLatLonBounds(tx, ty, zoom)

        lon_space = np.linspace(min_lon, max_lon, tile_size // sub_sample, endpoint=True)
        lat_space = -np.linspace(min_lat, max_lat, tile_size // sub_sample, endpoint=True)
        
        lon_space[lon_space < self.lon_bounds[0]] += 360
        lon_space[lon_space > self.lon_bounds[1]] -= 360
        
        grid = np.meshgrid(lon_space, lat_space)
        
        u, v = self.u_interp(grid), self.v_interp(grid)
        return u, v
    
    def rgba(self, u, v, tile_size):
        
            rgba = np.zeros([u.shape[0], u.shape[1], 4], dtype='uint8')
            hhh = np.zeros([u.shape[0], u.shape[1], 3])
            
            angle = np.arctan2(u, v)
            ang = (angle + np.pi) / (2 * np.pi)
            
            METERS_PER_SECOND = 3.0
            amp = np.sqrt(u ** 2 + v ** 2) / METERS_PER_SECOND
            amp = np.clip(amp, 0, METERS_PER_SECOND)
            
            hhh[:, :, 0] = ang
            hhh[:, :, 1] = np.sqrt(amp)
            hhh[:, :, 2] = (amp / 10) + .9
            
            rgba[:, :, 3] = 255
            rgba[:, :, :3] = hsv_to_rgb(hhh) * 255
            rgba[:, :, :3][u == 0] = 0
            
            return rgba
    
