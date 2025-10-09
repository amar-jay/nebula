Herelink Integration
====================

.. _herelink:

Overview
--------

This section covers the code and examples required to integrate Herelink with Nebula, including:

- MQ (ZeroMQ) manipulation and routing logic used to bridge telemetry/commands between the GCS and the Herelink link.
- Runtime behaviours such as link failover, telemetry relaying, and command passthrough.

.. note::

   Documentation for Herelink support is **in progress**. The code in the repository is usable
   now and shows how Nebula integrates with Herelink hardware, but the written docs are still
   being completed.


.. warning::

   Some hardware control and message-routing code touches sensitive subsystems (power control,
   serial passthrough, and low-level command forwarding). Exercise caution before modifying or
   deploying these components on a live system.

Recommended references
----------------------

.. admonition:: Read first
   :class: tip

   - Inspect the implementation directly in the repository for the most accurate, working examples.  
   - Consult the official Herelink / manufacturer documentation for hardware-specific wiring, RF
     regulations, and supported connection modes — use that as the authoritative reference when
     changing hardware or low-level configuration.  
   - Also read the project `README <https://github.com/amar-jay/nebula>`_ for overall setup and
     deployment notes.

Usage notes
-----------

- If you are testing with a real Herelink unit, validate wiring and power in a bench setup before flight.  
- For debugging, enable verbose logging on both the edge server and the GCS to trace MQ messages and
  serial traffic.  
- Treat any code that toggles hardware power or reconfigures serial ports as high-risk until reviewed.

API / Code entry points
-----------------------

.. autosumma
