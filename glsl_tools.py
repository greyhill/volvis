import pyglet.gl as gl
import ctypes as ct
import numpy as np

def rotation_matrix(deg, axis):
  rad = deg * np.pi / 180.0

  rot = np.eye(4)
  axes = [0,1,2]
  del axes[axis]

  # if i remembered my linear algebra better, i'd call this a plane
  # rotation
  rot[(axes[0], axes[1]), (axes[0], axes[0])] = ( np.cos(rad), np.sin(rad) )
  rot[(axes[0], axes[1]), (axes[1], axes[1])] = (-np.sin(rad), np.cos(rad) )

  return rot

def perspective_matrix(fov_deg, ratio, near, far):
  fov = fov_deg * np.pi / 180.0
  tfov = np.tan(fov)

  p = np.eye(4)
  p[0,0] = 1.0 / (fov * ratio)
  p[1,1] = 1.0 / fov
  p[2,2] = (far+near)/(far-near)
  p[3,2] = -1.0
  p[3,3] = 0.0
  p[2,3] = 2*(far+near)/(far-near)

  return p

class program(object):
  def __init__(self):
    self.__value = gl.glCreateProgram()

  def __del__(self):
    gl.glDeleteProgram(self.__value)

  def __get_value(self):
    return self.__value
  value = property(__get_value)

  def link(self):
    gl.glLinkProgram(self.__value)

    err_status = ct.c_int()
    gl.glGetProgramiv(self.__value, gl.GL_LINK_STATUS, 
        ct.byref(err_status))
    if err_status.value != gl.GL_TRUE:
      log_length = ct.c_int()
      gl.glGetProgramiv(self.__value, 
          gl.GL_INFO_LOG_LENGTH, 
          ct.byref(log_length))

      log_buf = (ct.c_char * (log_length.value))()
      log_buf_ptr = ct.cast( \
          ct.pointer(log_buf),
          ct.c_char_p)
      gl.glGetProgramInfoLog(self.__value, log_length.value,
          None, log_buf_ptr)

      raise GLException("Program failed to link:\n%s" % \
          log_buf.value)

class vertex_array(object):
  def __init__(self):
    self.__value = None
    buf = ct.c_uint()
    gl.glGenVertexArrays(1, ct.byref(buf))
    self.__value = buf.value

  def __del__(self):
    if self.__value is not None:
      buf = ct.c_uint()
      buf.value = self.__value
      gl.glDeleteVertexArrays(1, ct.byref(buf))

  def __get_value(self):
    return self.__value
  value = property(__get_value)

class texture(object):
  def __init__(self):
    self.__value = None
    buf = ct.c_uint()
    gl.glGenTextures(1, ct.byref(buf))
    self.__value = buf.value

  def __del__(self):
    if self.__value is not None:
      buf = ct.c_uint()
      buf.value = self.__value
      gl.glDeleteTextures(1, ct.byref(buf))

  def __get_value(self):
    return self.__value
  value = property(__get_value)

class buffer(object):
  def __init__(self):
    self.__value = None
    buf = ct.c_uint()
    gl.glGenBuffers(1, ct.byref(buf))
    self.__value = buf.value

  def __del__(self):
    if self.__value is not None:
      buf = ct.c_uint()
      buf.value = self.__value
      gl.glDeleteBuffers(1, ct.byref(buf))

  def __get_value(self):
    return self.__value
  value = property(__get_value)

class shader(object):
  def __init__(self, source, shader_type):
    self.__value = None
    type_dict = {"vert":gl.GL_VERTEX_SHADER, "geom":gl.GL_GEOMETRY_SHADER,
        "frag":gl.GL_FRAGMENT_SHADER}

    # create and compile shader
    shader = gl.glCreateShader(type_dict[shader_type])
    source_ptr = ct.c_char_p(source)
    source_ptr_ptr = ct.cast(
        ct.pointer(source_ptr),
        ct.POINTER(ct.POINTER(ct.c_char)) )
    gl.glShaderSource(shader, 1, source_ptr_ptr, None)
    gl.glCompileShader(shader)

    # check for error
    err_status = ct.c_int()
    gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS, ct.byref(err_status))
    if err_status.value != gl.GL_TRUE:
      # error occurred
      log_length = ct.c_int()
      gl.glGetShaderiv(shader, gl.GL_INFO_LOG_LENGTH,
          ct.byref(log_length))

      log_buffer = (ct.c_char * log_length.value)()
      log_buffer_ptr = ct.cast( \
          ct.pointer(log_buffer),
          ct.c_char_p)
      gl.glGetShaderInfoLog(shader, log_length.value, None,
          log_buffer_ptr)

      gl.glDeleteShader(shader)

      raise gl.GLException("Shader failed to compile: \n%s" % log_buffer.value)
    else:
      self.__value = shader

  def __del__(self):
    if self.__value is not None:
      gl.glDeleteShader(self.__value)

  def __get_value(self):
    return self.__value
  value = property(__get_value)

