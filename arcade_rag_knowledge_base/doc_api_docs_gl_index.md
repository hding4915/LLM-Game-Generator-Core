Source: doc/api_docs/gl/index.rst


# Arcade's Graphics Layer

The ``arcade.gl`` module is a "graphics layer" around platform-specific backends.

This module is meant to provide advanced users with:

#. a pluggable backend API for porting to new platforms
#. consistent abstractions of low-level graphics primitives
#. avoiding common pitfalls graphics programming


## Using This Module

This module **does not** aim to be a perfect copy of any other graphics API.


   This module assumes you are familiar with low-level graphics programming!

Instead, it takes inspiration from ModernGL_ to build on :py:mod:`pyglet.gl`
with more :py:mod:`ctypes` bindings.



The low-level API primitives and their reference implementation include:

   :header-rows: 1

   * - Primitive
     - Base (:py:mod:`arcade.gl`)
     - OpenGL Reference Subclass (:py:mod:`arcade.gl.backends.opengl`)

   * - GPU programs (shaders)
     - :py`program.Program <arcade.gl.program.Program>`
     - :py`~arcade.gl.backends.opengl.program.Program`

   * - low-level texture objects [#textureTypes]_
     - :py`arcade.gl.texture.Texture`
     - :py`~arcade.gl.backends.opengl.texture.Texture`

   * - framebuffers
     - :py`arcade.gl.framebuffer.Framebuffer`
     - :py`~arcade.gl.backends.opengl.framebuffer.Framebuffer`

   * - queries
     - :py`arcade.gl.query.Query`
     - :py`~arcade.gl.backends.opengl.query.Query`

   * - buffers
     - :py`arcade.gl.buffer.Buffer`
     - :py`~arcade.gl.backends.opengl.buffer.Buffer`

   * - vertex arrays/geometry
     - :py`arcade.gl.vertex_array.VertexArray`
     - :py`~arcade.gl.backends.opengl.vertex_array.VertexArray`

   * - Compute shaders [#macOS]_
     - :py`arcade.gl.compute_shader.ComputerShader`
     - :py`~arcade.gl.backends.opengl.compute_shader.ComputerShader`

Usage Reference
^^^^^^^^^^^^^^^


   * - Reference Backend
     - :py:mod:`arcade.gl.backends.opengl`

   * - Abstraction examples
     - See the `experimental examples`_ folder in the GitHub repo




## Graphics API Gotchas


No Computer Shaders On Mac
^^^^^^^^^^^^^^^^^^^^^^^^^^

This limitation is due to how macOS handles OpenGL.

Compute shaders became a core OpenGL feature in 4.3. However, Apple froze
OpenGL for macOS as a maintenance-only API at OpenGL 4.1 on both Intel and
M-series Macs. As a result, there are no compute shaders on Mac.

Alternatives
""""""""""""

Clever use of fragments shaders and framebuffer objects (FBOs) can
sometimes provide equivalent results for specific cases. Since WebGL
also lacks compute shaders, older WebGL code can be a useful reference
for implementing Mac-compatible compute functionality within OpenGL.


Two Texture Types?
^^^^^^^^^^^^^^^^^^

This module includes low-level and platform-specific classes.

Most users will want to use the high-lever :py`arcade.Texture`
class. If you are still unsure, consult the table below:


   * - Module
     - Target Audience
     - Contents

   * - :py:mod:`arcade.texture`
     - Everyday users
     - Friendly texture object suitable for implementing gameplay

   * - :py:mod:`arcade.gl.backends` ``texture`` submodules
     - Platform-specific internals
     - Low-level abstractions which handle platform-specific behavior for:

       * Low-level graphics APIs
       * Operating systems
       * Edge cases too specific to mention here


## Supported Backends

Current Backends
^^^^^^^^^^^^^^^^

OpenGL Backend
""""""""""""""

The current implemented backend is the OpenGL/GLES wrapper in :py:mod:`arcade.gl.backends.opengl`.

To maximize hardware support, it requires at least one of the following:

* OpenGL 3.3+
* GLES with certain extensions

It avoids binary dependencies by using Python's built-in :py:mod:`ctypes`
module via both :py:mod:`pyglet` and Arcade's added OpenGL bindings.

This ensures Arcade can run on most desktop and laptop hardware from the past
decade, just like :py:mod:`pyglet`. This portability trades away a bit of speed
and context-handling flexibility compared to ModernGL_.

Future Backends
^^^^^^^^^^^^^^^

Web
"""

Web browser support is an ongoing effort.

The current plan is to implement a WebGPU backend running locally in-browser
via pyodide. This will ensure better performance and feature parity with desktop
environments compared to the archived `arcade-web`_ protoype.


Adding Backends
"""""""""""""""

A new backend requires adding a submodule in :py:mod:`arcade.gl.backends`
which handles any initialization tasks to implement the following:

* concreted versions of the classes in arcade-api-gl-usage
* exposes a concrete implementation of :py`~arcade.gl.provider.BaseProvider`

Note that all resources are created through the
:py`arcade.gl.Context` / :py`arcade.ArcadeContext`.
An instance of this type should be accessible the window
(:py:attr:`arcade.Window.ctx`).

This API can also be used with pyglet by creating an instance
of :py`arcade.gl.Context` after the window creation.
The :py`arcade.ArcadeContext` on the other hand
extends the default Context with Arcade-specific helper methods
and should only be used by arcade.

   :maxdepth: 1

   context
   texture
   texture_array
   buffer
   geometry
   framebuffer
   query
   program
   sampler
   exceptions
   types

