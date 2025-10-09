Welcome to Nebula's documentation!
===================================

`Nebula <https://github.com/amar-jay/nebula>`_ is a software project for drone control and automation. It was primarily made as part of the **Nebula MATEK Team** for the [Teknofest 2025](https://teknofest.org/en/) competition, which was 
sponsored by the Çemberlitaş Gençlik Merkezi (/chem-ber-lee-tash gench-lik mer-ke-zi/).

Nebula has a number of components:

1. A ground control station application for remotely monitoring and controlling the drone.

2. A remote server running on an edge device (NVIDIA Jetson Orin NX) for processing data and interfacing with the drone, as well as giving serial commands to the crane of the drone.

3. Both are interfacing with each other via ZeroMQ as a messaging protocol.

Check out the :doc:`usage` section for further information, including
how to :ref:`installation` the project.

.. image:: https://img.youtube.com/vi/ZF_N-Vu7Tik/maxresdefault.jpg
   :width: 25%
   :height: auto
   :target: https://www.youtube.com/watch?v=ZF_N-Vu7Tik
   :alt: System Demo

.. note::

   This project is no longer under development, since the competition is over.

Contents
--------

.. toctree::

   usage
   messaging
   api
