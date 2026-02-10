Source: doc/example_code/drawing_text_objects_batch.rst

:orphan:


# The Fastest Text Drawing: pyglet Batches

    :width: 500px
    :align: center
    :alt: Screenshot of drawing with text objects

This example demonstrates the most efficient way to render
:py`arcade.Text` objects: adding them to pyglet's
:py`~pyglet.graphics.Batch`. Otherwise, it is the
same as the drawing_text_objects example.

For a much simpler and slower approach,  see drawing_text.

    :caption: drawing_text_objects.py
    :linenos:
