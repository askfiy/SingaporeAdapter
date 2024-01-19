# SingaporeAdapter

## Project Description

Singapore Xizi project signal middleware adapter.

This project is a customized signal middleware for the Singapore West Subproject, using the Mitsubishi MC protocol. Pure Python asynchronous implementation.

Based on asyncio-tcp and self-encapsulated mc signal unpacking mode.

External services use aiohttp server to build an api gateway for communicating with GzRobot's AGV car.

The main function of this project is to connect GzRobot’s internal protocol signals with Xizi’s elevators.

## Address table

See the conf/private/signal.json file.

For signals and their functions, contact the person in charge of the actual docking party.

## Design Ideas

The software is divided into 3 layers:

- adapter (docking layer)
- device (virtual physical device layer)
- service (external service layer)

The Adapter layer is mainly responsible for business logic processing and converting requests from the service layer to the device layer.

As a mapping of real physical devices, the Device layer abstracts the boring signal sending and receiving methods of physical devices into various independent interfaces for easy calling. It mainly aims at simulating the client's elevator equipment and provides various query and writing interfaces.

The Service layer mainly processes the signals sent by the AGV inside Gzrobot and transfers them to specific devices through the adapter layer.

```
                     Business logic
  ┌───────────┐      ┌───────────┐        ┌───────────┐
  │           │      │           │        │           │
  │           │      │           │        │           │
  │           │ req  │           │ req    │           │
  │  service  ├─────►│  adapter  │──────► │  device   │
  │           │      │           │        │           │
  │           │      │           │        │           │
  │           │      │           │        │           │
  └───────────┘      └───────────┘        └───────────┘
```

Others, utils encapsulate simple calls to various libraries. Such as asyncio-tcp-client's advanced encapsulation, mc protocol encapsulation, etc..
