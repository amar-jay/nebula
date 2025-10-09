Welcome to Nebula's documentation!
===================================

.. raw:: html

   <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; width: 100%;">
       <iframe src="https://www.youtube.com/embed/ZF_N-Vu7Tik"
               title="Nebula System Demo"
               frameborder="0"
               allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
               allowfullscreen
               style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
       </iframe>
   </div>

`Nebula <https://github.com/amar-jay/nebula>`_ is a software system for drone control and automation.  
It was developed by the **Nebula MATEK Team** for the `Teknofest 2025 <https://teknofest.org/en/>`_ competition,  
sponsored by the **Çemberlitaş Gençlik Merkezi** *(pronounced /chem-ber-lee-tash gench-lik mer-ke-zi/)*.

Nebula consists of several core components:

1. **Ground Control Station (GCS):** A desktop application for remotely monitoring and controlling the drone.

2. **Edge Server:** Runs on an NVIDIA Jetson Orin NX for data processing, drone interfacing,  
   and sending serial commands to the crane subsystem.

3. **ZeroMQ Communication:** Provides a lightweight and fast messaging layer between the GCS and the edge server.

.. note::

   This project is no longer under development, since the competition is over.

Refer to the :doc:`usage` section for detailed usage instructions and  
see :ref:`installation` for setup guidance.



Contents
--------

.. toctree::

   usage
   messaging
   herelink
   gps_estimation
   gazebo_simulation
   ground_control_station
   api
