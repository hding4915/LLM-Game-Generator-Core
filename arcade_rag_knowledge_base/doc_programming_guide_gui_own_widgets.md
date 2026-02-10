Source: doc/programming_guide/gui/own_widgets.rst


## Own Widgets

Creating your own widgets is a powerful feature of the GUI module.
It allows you to create custom widgets that can be used in your application.

In most cases this is even the easiest way to implement your desired interface.

The following sections will guide you through the process of creating own widgets.



Where to start
~~~~~~~~~~~~~~

To create your own widgets, you need to create a new class that inherits from `arcade.gui.UIWidget`.

While inheriting from `arcade.gui.UIWidget`, provides the highest flexibility.
The main methods you need to implement are:
- :meth:`arcade.gui.UIWidget.do_render` - This method is called to render the widget.
- :meth:`arcade.gui.UIWidget.on_event` - This method is called to handle events like mouse or keyboard input.
- :meth:`arcade.gui.UIWidget.on_update` - This method is called to update the widget (same frequency like window).

You can also make use of other base classes, which provide a more specialized interface.
Further baseclasses are:

- `arcade.gui.UIInteractiveWidget`
    A base class for widgets that can be interacted with.
    It handles mouse events and provides properties like `hovered` or `pressed` and an :meth:`~arcade.gui.UIInteractiveWidget.on_click` method.

- `arcade.gui.UIAnchorLayout`
    Basically a frame, which can be used to place widgets
    to a position within itself. This makes it a great base class for a widget containing
    multiple other widgets. (Examples: `MessageBox`, `Card`, etc.)

If your widget should act more as a general layout, position various widgets and handle their size,
you should inherit from `arcade.gui.UILayout` instead.

In the following example, we will create two progress bar widgets
to show the differences between two of the base classes.


Example `ProgressBar`
~~~~~~~~~~~~~~~~~~~~~



