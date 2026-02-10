Source: doc/programming_guide/sprites/spritelists.rst


## Drawing with Sprites and SpriteLists

What's a Sprite?
^^^^^^^^^^^^^^^^

Each sprite describes where a game object is & how to draw it. This includes:

* Where it is in the world
* Where to find the image data
* How big the image should be

The rest of this page will explain using the :py`~arcade.SpriteList` class to draw
sprites to the screen.



Why SpriteLists?
^^^^^^^^^^^^^^^^


They're How Hardware Works
""""""""""""""""""""""""""

Graphics hardware is designed to draw groups of objects at the same time.
These groups are called **batches**.

Each :py`~arcade.SpriteList`
automatically translates every :py`~arcade.Sprite` in it
into an optimized batch. It doesn't matter if a batch has one or hundreds of
sprites: it still takes the same amount of time to draw!

This means that using fewer batches helps your game run faster, and that you
should avoid trying to draw sprites one at a time.



They Help Develop Games Faster
""""""""""""""""""""""""""""""

Sprite lists do more than just draw. They also have built-in features which save
you time & effort, including:

* Automatically skipping off-screen sprites
* Collision detection
* Debug drawing for hit boxes



Using Sprites and SpriteLists
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's get to the example code.

There are 3 steps to drawing sprites with a sprite list:

1. Create a :py`~arcade.SpriteList`
2. Create & append your :py`~arcade.Sprite` instance(s) to the list
3. Call :py:meth:`~arcade.SpriteList.draw` on your SpriteList inside an
   :py:meth:`~arcade.Window.on_draw` method

Here's a minimal example:

    :caption: sprite_minimal.py
    :linenos:


Using Images with Sprites
^^^^^^^^^^^^^^^^^^^^^^^^^

Beginners should see the following to learn more, such as how to load images
into sprites:

* Arcade's Sprite examples <sprite_examples>
* Arcade's Simple Platformer Tutorial <platformer_tutorial>
* The :py`~arcade.Sprite` API documentation


Viewports, Cameras, and Screens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Intermediate users can move past the limitations of :py`arcade.Window`
with the following classes:

* :py`arcade.Camera2D` (examples <camera_examples>) to control which part of game space is drawn
* :py`arcade.View` (examples <view_examples>) for start, end, and menu screens
