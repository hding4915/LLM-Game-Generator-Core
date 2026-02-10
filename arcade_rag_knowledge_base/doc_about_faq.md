Source: doc/about/faq.rst


# Frequently asked questions


## Can I use Arcade resources in my own educational materials?


Yes! Arcade was originally developed for educational use. In addition to
a page academia, we have further documentation covering:


* The permissive_mit covers the library and documentation
* The CC0 Public Domain Dedication <permissive_almost_all_public> and similar cover the resources


## Can I use Arcade in a commercial project?

commercial_games. There's already one commercially released game using Arcade.


## Can I copy and adapt example code for my own projects?

Of course! We encourage you to do so. That's why the example code is there: we
want you to learn and be successful. See the permissive_mit section to learn
more about Arcade's license means (you agree not to claim you wrote the whole thing).

## Can Arcade run on...?

Windows, Mac, and Linux
^^^^^^^^^^^^^^^^^^^^^^^

Yes. Most hardware with an Intel or AMD processor from the last ten years will do fine.
New requirements_mac_mseries can have some hiccups, but they generally work.


Raspberry Pi and Other SBCs
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Raspberry Pi is a popular brand of Single Board Computers (SBCs).

The Raspberry Pi 4 and 5 can run Arcade under `Raspberry Pi OS`_,
and the Raspberry Pi 400 *may* also work. As of October 2024,
All other other Raspberry Pi models are incompatible <sbc_unsupported_raspis>.

Other SBCs *may* work with Arcade 3.0.0. See the sbc_requirements to learn more.


Web
^^^
Not yet. For the moment, the Arcade and `pyglet`_ teams are eagerly
watching ongoing developments in `WebGPU`_ and its `WASM`_ integrations.



Mobile
^^^^^^
Not in the near future. Supporting mobile requires big changes to both
Arcade and the `pyglet`_ library we use.


Android
"""""""
Android support will take a huge amount of work:

#. `pyglet`_ would need to account for mobile-specific OS behavior
#. Arcade would need to make changes to account for mobile as well
#. Not all devices will support the necessary OpenGL ES versions <requirements_gles>.


iOS and iPad
""""""""""""

Not in the foreseeable future. They are much trickier than web or Android
for a number of reasons. For near-future iOS and iPad support, you may want to
to try `Kivy`_.


