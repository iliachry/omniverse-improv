# Omniverse Improv Starter Extension

`omni.improv.starter` is an Omniverse Kit extension providing an interactive, dockable UI toolset for procedural USD scene generation, rapid physics asset spawning, and real-time scene tweaking.

## Features
- **Interactive UI**: Built with `omni.ui` following NVIDIA Omniverse design patterns.
- **Procedural Arena Spawner**: Instantly spawns a ground plane, physics boundaries, and studio lighting rig.
- **Rigid Body Spawner**: Spawns cubes, spheres, capsules, and dominoes with pre-configured `UsdPhysics.RigidBodyAPI` and collision approximations.
- **Physics Parameter Manager**: Real-time adjustment of stage gravity, static/dynamic friction, restitution (bounciness), and mass density.
- **Material Presets**: Quickly apply glowing neon, brushed metal, rubber, or glass PBR shaders to selected USD prims.

## How to Enable in Omniverse (USD Composer / Kit App)
1. Open Omniverse USD Composer / Kit App.
2. Go to **Window > Extensions**.
3. Click the **Gear icon (Extension Manager Settings)** and add the path to the `exts` directory:
   `<your-repo-path>/exts`
4. Search for `Omniverse Improv Starter` in the Community / Third Party tab.
5. Toggle the switch to **ON**.
6. Access the panel from the top menu: **Window > Improv Starter**.
