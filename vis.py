import pyglet as pyg
import pyglet.gl as gl
import numpy as np
import threading as th
import glsl_tools as util
import ctypes as ct

class visualizer(object):
  def __init__(self, width=640, height=480, fullscreen=False):
    # create the window
    self.__width = width
    self.__height = height
    self.__fullscreen = fullscreen
    self.__data_lock = th.RLock()
    self.__window = None
    self.__data_altered = False
    self.__data = np.zeros( (1,1,1) )
    
    # some default values
    self.bg_color = [ 0.0, 0.0, 0.0, 1.0 ]
    self.caption = ""
    self.rots = [ 0.0, 0.0, 0.0 ]
    self.zoom = 1.0
    self.voxel_spacing = [ 1.0, 1.0, 1.0 ]
    self.voxel_size = [ 1.0, 1.0, 1.0 ]
    self.location = [ 0, 0, 3.0 ]
    self.opacity = 1.0
    self.min_value = 0.0
    self.saturation_value = 0.0
    self.downsample = 1

    # start background thread with TERRIBLE HORRIBLE KLUDGE
    import time
    num_tries = 0
    while num_tries < 10:
      try:
        self.__thread = th.Thread( target=lambda: self.__run() )
        self.__thread.start()
        break
      except:
        time.sleep(.2)
        num_tries += 1

  def __run(self):
    self.__window = pyg.window.Window( \
        width=self.__width,
        height=self.__height,
        fullscreen=self.__fullscreen)

    # setup some GL stuff
    self.__setup_shaders()
    self.__setup_geometry_buffer()
    self.__data_texture = None
    self.__vao = None

    # register event handlers
    self.__window.set_handler("on_draw", self.__draw)
    self.__window.set_handler("on_mouse_drag", self.__mouse_drag)
    self.__window.set_handler("on_key_release", self.__key_release)

    try:
      pyg.app.run()
    except Exception, e:
      print "visualizer exception: %s\n" % e

  def wait(self):
    self.__thread.join()

  def stop(self):
    pyg.app.exit()
    self.wait()

  def __mouse_drag(self, x, y, dx, dy, buttons, modifiers):
    self.__rots[1] -= dx
    self.__rots[0] -= dy

  def __key_release(self, symbol, modifiers):
    if symbol == pyg.window.key.EQUAL:
      self.zoom *= 1.1
    elif symbol == pyg.window.key.MINUS:
      self.zoom /= 1.1
    elif symbol == pyg.window.key.BRACKETLEFT:
      self.opacity /= 1.1
    elif symbol == pyg.window.key.BRACKETRIGHT:
      self.opacity *= 1.1

  def __setup_shaders(self):
    import os
    vertex_source_path = os.path.sep.join( [\
        os.path.dirname(os.path.realpath(__file__)),
        "vs_vert.glsl"])
    vertex_source = open(vertex_source_path, "r").read()
    self.__vert_shader = util.shader(vertex_source, "vert")

    frag_source_path = os.path.sep.join( [\
        os.path.dirname(os.path.realpath(__file__)),
        "vs_frag.glsl"])
    frag_source = open(frag_source_path, "r").read()
    self.__frag_shader = util.shader(frag_source, "frag")

    self.__prog = util.program()
    gl.glAttachShader(self.__prog.value, self.__vert_shader.value)
    gl.glAttachShader(self.__prog.value, self.__frag_shader.value)
    self.__prog.link()

  def __setup_geometry_buffer(self):
    data_buffer = ((ct.c_float*3)*36)()
    # {{{ vertex data for cube
    v0 = ( .5, .5, .5 )
    v1 = ( -.5, .5, .5 )
    v2 = ( -.5, -.5, .5 )
    v3 = ( .5, -.5, .5 )
    v4 = ( .5, .5, -.5 )
    v5 = ( -.5, .5, -.5 )
    v6 = ( -.5, -.5, -.5 )
    v7 = ( .5, -.5, -.5 )

    data_buffer[0:3] = (v4, v0, v7)
    data_buffer[3:6] = (v0, v3, v7)
    data_buffer[6:9] = (v0, v1, v2)
    data_buffer[9:12] = (v0, v2, v3)
    data_buffer[12:15] = (v5, v1, v0)
    data_buffer[15:18] = (v5, v0, v4)
    data_buffer[18:21] = (v3, v6, v7)
    data_buffer[21:24] = (v3, v2, v6)
    data_buffer[24:27] = (v2, v1, v6)
    data_buffer[27:30] = (v6, v1, v5)
    data_buffer[30:33] = (v4, v6, v5)
    data_buffer[33:36] = (v7, v6, v4)
    # }}}

    data_ptr = ct.cast(ct.pointer(data_buffer),
        ct.POINTER(ct.c_float))

    # create GL buffer
    self.__geom_buffer = util.buffer()
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.__geom_buffer.value)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, ct.sizeof(data_buffer),
        data_ptr,
        gl.GL_STATIC_DRAW)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

  def __setup_data_buffer(self):
    data_ptr = ct.cast( np.ctypeslib.as_ctypes(self.__data),
        ct.POINTER(ct.c_float) )

    self.__data_buffer = util.buffer()
    gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, self.__data_buffer.value)
    gl.glBufferData(gl.GL_TEXTURE_BUFFER, 
        ct.sizeof(ct.c_float)*self.__data.size,
        data_ptr,
        gl.GL_STATIC_DRAW)

    if self.__data_texture is None:
      self.__data_texture = util.texture()
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.__data_texture.value)

    gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_R32F, 
        self.__data_buffer.value)

    self.__data_altered = False

  def __draw(self):
    gl.glClearColor(self.__bg_color[0],
        self.__bg_color[1],
        self.__bg_color[2],
        self.__bg_color[3])
    gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
    gl.glUseProgram(self.__prog.value)

    # update data buffer if necessary
    with self.__data_lock:
      if self.__data_altered:
        self.__setup_data_buffer()

    self.__set_uniforms()
    self.__set_attributes()

    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE)
    gl.glEnable(gl.GL_BLEND)
    gl.glEnable(gl.GL_CULL_FACE)
    gl.glDrawArraysInstanced(gl.GL_TRIANGLES,
        0, 36, self.__data.size / (self.__downsample**3))

  def __set_uniforms(self):
    # projection matrix (proj)
    proj_loc = gl.glGetUniformLocation(self.__prog.value, "proj")
    proj_matrix = self.__proj_matrix()
    proj_matrix_ptr = ct.cast( \
        ct.pointer(np.ctypeslib.as_ctypes(proj_matrix)),
        ct.POINTER(ct.c_float) )
    gl.glUniformMatrix4fv(proj_loc, 1, gl.GL_TRUE, 
        proj_matrix_ptr)

    # voxel spacing
    voxel_spacing_loc = gl.glGetUniformLocation(self.__prog.value,
        "voxel_spacing")
    gl.glUniform3f(voxel_spacing_loc,
        self.__voxel_spacing[0]*self.__downsample,
        self.__voxel_spacing[1]*self.__downsample,
        self.__voxel_spacing[2]*self.__downsample)

    # voxel size
    voxel_size_loc = gl.glGetUniformLocation(self.__prog.value,
        "voxel_size")
    gl.glUniform3f(voxel_size_loc,
        self.__voxel_size[0]*self.__downsample,
        self.__voxel_size[1]*self.__downsample,
        self.__voxel_size[2]*self.__downsample)

    # data; not technically a "uniform" but a texture
    data_loc = gl.glGetUniformLocation(self.__prog.value,
        "data")
    gl.glUniform1i(data_loc, 0)

    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.__data_texture.value)

    # dims
    dims_loc = gl.glGetUniformLocation(self.__prog.value,
        "dims")
    gl.glUniform3i(dims_loc,
        self.__data.shape[0]/self.__downsample,
        self.__data.shape[1]/self.__downsample,
        self.__data.shape[2]/self.__downsample)

    # global_opacity
    global_opacity_loc = gl.glGetUniformLocation(self.__prog.value,
        "global_opacity")
    gl.glUniform1f(global_opacity_loc, self.__opacity)

    # min value
    min_value_loc = gl.glGetUniformLocation(self.__prog.value,
        "min_value")
    gl.glUniform1f(min_value_loc, self.__min_value)

    # saturation value
    saturation_value_loc = gl.glGetUniformLocation(self.__prog.value,
        "saturation_value")
    gl.glUniform1f(saturation_value_loc, self.__saturation_value)

    # downsample
    downsample_loc = gl.glGetUniformLocation(self.__prog.value,
        "downsample")
    gl.glUniform1i(downsample_loc, self.__downsample)

  def __set_attributes(self):
    if self.__vao is None:
      self.__vao = util.vertex_array()
    gl.glBindVertexArray(self.__vao.value)

    # coord
    coord_loc = gl.glGetAttribLocation(self.__prog.value, "coord")
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.__geom_buffer.value)
    gl.glVertexAttribPointer(coord_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, 0)
    gl.glEnableVertexAttribArray(coord_loc)

  def __proj_matrix(self):
    proj = util.perspective_matrix(fov_deg = 90, 
        ratio = float(self.__width) / float(self.__height),
        near = .1,
        far = 20.0)

    mv = np.eye(4)
    mv[0:3,3] = -1.0 * self.__location
    for a in (0,1,2):
      mv = np.dot(mv, 
          util.rotation_matrix(deg=self.__rots[a], axis=a))
    mv[0:3,0:3] *= self.__zoom

    res = np.dot(proj, mv)

    return np.array(res, dtype="float32")

  def __get_bg_color(self): 
    return self.__bg_color
  def __set_bg_color(self, c): 
    self.__bg_color = np.array(c, dtype="float32")
  bg_color = property(__get_bg_color, __set_bg_color)

  def __get_caption(self):
    return self.__caption
  def __set_caption(self, c):
    self.__caption = c
    if self.__window is not None:
      self.__window.set_caption(c)
  caption = property(__get_caption, __set_caption)

  def __get_rots(self):
    return self.__rots
  def __set_rots(self, r):
    self.__rots = np.array(r, dtype="float32")
  rots = property(__get_rots, __set_rots)

  def __get_zoom(self):
    return self.__zoom
  def __set_zoom(self, z):
    self.__zoom = np.array(z, dtype="float32")
  zoom = property(__get_zoom, __set_zoom)

  def __get_voxel_spacing(self):
    return self.__voxel_spacing
  def __set_voxel_spacing(self, vs):
    self.__voxel_spacing = np.array(vs, dtype="float32")
  voxel_spacing = property(__get_voxel_spacing, __set_voxel_spacing)

  def __get_voxel_size(self):
    return self.__voxel_size
  def __set_voxel_size(self, vs):
    self.__voxel_size = np.array(vs, dtype="float32")
  voxel_size = property(__get_voxel_size, __set_voxel_size)

  def __get_data(self):
    return self.__data
  def __set_data(self, d):
    with self.__data_lock:
      self.__data = np.array(d, dtype="float32", order="C")
      self.__data_altered = True
      self.guess_zoom()
      self.guess_data_bounds()
  data = property(__get_data, __set_data)

  def __get_location(self):
    return self.__location
  def __set_location(self, l):
    self.__location = np.array(l, dtype="float32")
  location = property(__get_location, __set_location)

  def __get_opacity(self):
    return self.__opacity
  def __set_opacity(self, o):
    self.__opacity = float(o)
  opacity = property(__get_opacity, __set_opacity)

  def __get_min_value(self):
    return self.__min_value
  def __set_min_value(self, v):
    self.__min_value = float(v)
  min_value = property(__get_min_value, __set_min_value)

  def __get_saturation_value(self):
    return self.__saturation_value
  def __set_saturation_value(self, v):
    self.__saturation_value = float(v)
  saturation_value = property(__get_saturation_value,
      __set_saturation_value)

  def __get_downsample(self):
    return self.__downsample
  def __set_downsample(self, v):
    self.__downsample = int(v)
  downsample = property(__get_downsample, __set_downsample)

  def guess_zoom(self):
    obj_distance = np.linalg.norm(self.__location)
    near_clip_distance = .1
    diag_len = np.linalg.norm( (np.array(self.__data.shape) * self.__voxel_spacing \
        + self.__voxel_size) / 4.0 )
    self.zoom = abs( obj_distance - near_clip_distance ) / diag_len
    print self.zoom

  def guess_data_bounds(self):
    self.__min_value = np.min(self.__data)
    self.__saturation_value = np.max(self.__data)

