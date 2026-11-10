import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Html, RoundedBox, Sparkles } from "@react-three/drei";
import { DoubleSide, Plane, Vector2, Vector3, type Group, type Mesh, type Object3D } from "three";
import type { RiskLevel } from "../types";

export type HotspotId = "breathing" | "board" | "window" | "shelf";

interface Palette {
  floor: string;
  wall: string;
  accent: string;
  fog: string;
  fogNear: number;
  fogFar: number;
  particles: number;
  breath: number;
  light: number;
}

const PALETTE: Record<RiskLevel, Palette> = {
  normal: {
    floor: "#101a20", wall: "#0d1620", accent: "#2fbf71", fog: "#0a1a16",
    fogNear: 7, fogFar: 24, particles: 60, breath: 0.9, light: 18,
  },
  mild: {
    floor: "#1a1710", wall: "#15130d", accent: "#e0b32c", fog: "#171207",
    fogNear: 6, fogFar: 21, particles: 85, breath: 1.2, light: 17,
  },
  moderate: {
    floor: "#1d1410", wall: "#17110d", accent: "#e07b39", fog: "#1b1008",
    fogNear: 5, fogFar: 18, particles: 110, breath: 1.5, light: 16,
  },
  severe: {
    floor: "#1d1010", wall: "#170d0d", accent: "#d64b4b", fog: "#1c0a0a",
    fogNear: 4, fogFar: 15, particles: 140, breath: 1.9, light: 15,
  },
};

function BreathingOrb({
  color,
  speed,
  onSelect,
  active,
}: {
  color: string;
  speed: number;
  onSelect: () => void;
  active: boolean;
}) {
  const core = useRef<Mesh>(null);
  const halo = useRef<Mesh>(null);
  const outer = useRef<Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const scale = 1 + Math.sin(t * speed) * 0.12;
    if (core.current) {
      core.current.scale.setScalar(scale);
    }
    if (halo.current) {
      halo.current.scale.setScalar(1 + Math.sin(t * speed + 0.6) * 0.1);
      halo.current.rotation.z = t * 0.12;
    }
    if (outer.current) {
      outer.current.rotation.y = t * 0.05;
      outer.current.rotation.x = t * 0.03;
    }
  });

  return (
    <group position={[0, 1.55, -2.4]}>
      <mesh onClick={onSelect} visible={false}>
        <sphereGeometry args={[1.0, 16, 16]} />
      </mesh>
      <mesh ref={core} onClick={onSelect}>
        <sphereGeometry args={[0.42, 48, 48]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={active ? 1.6 : 1.0}
          roughness={0.2}
        />
      </mesh>
      <mesh ref={halo} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.42, 0]}>
        <ringGeometry args={[active ? 0.9 : 0.72, active ? 1.12 : 0.8, 64]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.85 : 0.45} />
      </mesh>
      <mesh ref={outer}>
        <icosahedronGeometry args={[1.05, 1]} />
        <meshBasicMaterial color={color} transparent opacity={0.06} wireframe />
      </mesh>
      <Html center distanceFactor={9} position={[0, 0.82, 0]} wrapperClass="hotspot-tag-wrap">
        <div className={active ? "hotspot-tag active" : "hotspot-tag"}>呼吸引导</div>
      </Html>
    </group>
  );
}

function HotspotNode({
  position,
  color,
  onSelect,
  phase,
  label,
  active,
}: {
  position: [number, number, number];
  color: string;
  onSelect: () => void;
  phase: number;
  label: string;
  active: boolean;
}) {
  const ring = useRef<Mesh>(null);

  useFrame((state) => {
    if (!ring.current) return;
    const scale = 1 + Math.sin(state.clock.elapsedTime * 2.2 + phase) * 0.14;
    ring.current.scale.setScalar(scale);
  });

  return (
    <group position={position}>
      <mesh onClick={onSelect} visible={false}>
        <sphereGeometry args={[0.58, 16, 16]} />
      </mesh>
      <mesh onClick={onSelect}>
        <sphereGeometry args={[0.15, 20, 20]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={active ? 2.6 : 1.6}
        />
      </mesh>
      <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.28, active ? 0.46 : 0.34, 32]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.9 : 0.55} />
      </mesh>
      <Html
        center
        distanceFactor={9}
        position={[0, 0.42, 0]}
        wrapperClass="hotspot-tag-wrap"
      >
        <div className={active ? "hotspot-tag active" : "hotspot-tag"}>{label}</div>
      </Html>
    </group>
  );
}

function GroundRings({ color }: { color: string }) {
  const rings = useRef<Group>(null);

  useFrame((state) => {
    if (!rings.current) return;
    rings.current.rotation.z = state.clock.elapsedTime * 0.02;
  });

  return (
    <group ref={rings} position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      {[2.4, 3.6, 5.2].map((radius, index) => (
        <mesh key={radius}>
          <ringGeometry args={[radius, radius + 0.05, 96]} />
          <meshBasicMaterial color={color} transparent opacity={0.3 - index * 0.08} />
        </mesh>
      ))}
    </group>
  );
}

function FloatingShard({
  position,
  color,
  phase,
  scale,
}: {
  position: [number, number, number];
  color: string;
  phase: number;
  scale: number;
}) {
  const shard = useRef<Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (!shard.current) return;
    shard.current.rotation.x = t * 0.12 + phase;
    shard.current.rotation.y = t * 0.16 + phase;
    shard.current.position.y = position[1] + Math.sin(t * 0.55 + phase) * 0.2;
  });

  return (
    <mesh ref={shard} position={position} scale={scale}>
      <icosahedronGeometry args={[0.26, 0]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.55}
        transparent
        opacity={0.5}
        flatShading
      />
    </mesh>
  );
}

function LightBeam({
  position,
  height,
  color,
}: {
  position: [number, number, number];
  height: number;
  color: string;
}) {
  return (
    <mesh position={[position[0], height / 2, position[2]]}>
      <cylinderGeometry args={[0.06, 0.2, height, 12, 1, true]} />
      <meshBasicMaterial color={color} transparent opacity={0.1} side={DoubleSide} />
    </mesh>
  );
}

function AbstractPanel({
  position,
  color,
  active,
  onSelect,
}: {
  position: [number, number, number];
  color: string;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <group position={position}>
      <mesh onClick={onSelect}>
        <planeGeometry args={[2.6, 1.6]} />
        <meshStandardMaterial
          color="#0a121e"
          emissive={color}
          emissiveIntensity={active ? 0.55 : 0.22}
          transparent
          opacity={0.85}
          side={DoubleSide}
        />
      </mesh>
      {[0.45, 0.15, -0.15, -0.45].map((y, index) => (
        <mesh key={y} position={[-0.2, y, 0.02]}>
          <planeGeometry args={[1.8 - index * 0.2, 0.03]} />
          <meshBasicMaterial color={color} transparent opacity={0.6} />
        </mesh>
      ))}
      <mesh position={[0, 0, 0.01]}>
        <planeGeometry args={[2.7, 1.7]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.16 : 0.07} />
      </mesh>
    </group>
  );
}

function LightGate({
  position,
  color,
  active,
  onSelect,
}: {
  position: [number, number, number];
  color: string;
  active: boolean;
  onSelect: () => void;
}) {
  const width = 2.4;
  return (
    <group position={position}>
      {[-width / 2, width / 2].map((x) => (
        <mesh key={x} position={[x, 0, 0]}>
          <boxGeometry args={[0.07, 2.6, 0.07]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
        </mesh>
      ))}
      <mesh position={[0, 1.32, 0]}>
        <boxGeometry args={[width + 0.07, 0.07, 0.07]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
      </mesh>
      <mesh onClick={onSelect}>
        <planeGeometry args={[width, 2.6]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={active ? 0.18 : 0.07}
          side={DoubleSide}
        />
      </mesh>
    </group>
  );
}

function MemoryPillar({
  position,
  color,
  active,
  onSelect,
}: {
  position: [number, number, number];
  color: string;
  active: boolean;
  onSelect: () => void;
}) {
  const orbit = useRef<Group>(null);

  useFrame((state) => {
    if (orbit.current) {
      orbit.current.rotation.y = state.clock.elapsedTime * 0.25;
    }
  });

  return (
    <group position={position}>
      <mesh onClick={onSelect}>
        <cylinderGeometry args={[0.18, 0.26, 2.2, 20, 1, true]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={active ? 0.9 : 0.4}
          transparent
          opacity={0.5}
          side={DoubleSide}
        />
      </mesh>
      <mesh onClick={onSelect} position={[0, 1.2, 0]}>
        <sphereGeometry args={[0.13, 18, 18]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={active ? 1.8 : 1.1}
        />
      </mesh>
      <group ref={orbit}>
        {[0, 1, 2, 3].map((index) => (
          <mesh
            key={index}
            position={[
              Math.cos(index * 1.6) * 0.55,
              1.15 + (index % 2) * 0.22,
              Math.sin(index * 1.6) * 0.55,
            ]}
          >
            <boxGeometry args={[0.09, 0.09, 0.09]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.7} />
          </mesh>
        ))}
      </group>
    </group>
  );
}

const TABLE_X = -4.2;
const TABLE_Z = 3.6;
const TABLE_TOP = 0.96;

type BlockShape = "box" | "cylinder" | "cone" | "sphere" | "tetra";

interface BlockSpec {
  id: number;
  shape: BlockShape;
  size: [number, number, number];
  color: string;
  position: [number, number, number];
}

const BLOCK_SCALE = 0.72;

const BASE_BLOCKS: BlockSpec[] = [
  { id: 1, shape: "box", size: [0.5, 0.4, 0.5], color: "#d9b382", position: [TABLE_X - 0.8, TABLE_TOP + 0.2, TABLE_Z - 0.5] },
  { id: 2, shape: "cylinder", size: [0.36, 0.42, 0.36], color: "#b07b4f", position: [TABLE_X + 0.1, TABLE_TOP + 0.21, TABLE_Z + 0.3] },
  { id: 3, shape: "cone", size: [0.38, 0.5, 0.38], color: "#8c5a38", position: [TABLE_X + 0.9, TABLE_TOP + 0.25, TABLE_Z - 0.6] },
  { id: 4, shape: "sphere", size: [0.34, 0.34, 0.34], color: "#e0c39a", position: [TABLE_X - 1.1, TABLE_TOP + 0.17, TABLE_Z + 0.7] },
  { id: 5, shape: "tetra", size: [0.42, 0.42, 0.42], color: "#7fa8c9", position: [TABLE_X + 0.3, TABLE_TOP + 0.2, TABLE_Z - 1.1] },
  { id: 6, shape: "box", size: [0.62, 0.24, 0.34], color: "#c9a06a", position: [TABLE_X + 0.7, TABLE_TOP + 0.12, TABLE_Z + 0.8] },
  { id: 7, shape: "cylinder", size: [0.28, 0.5, 0.28], color: "#a9784f", position: [TABLE_X - 0.3, TABLE_TOP + 0.25, TABLE_Z + 1.0] },
  { id: 8, shape: "box", size: [0.4, 0.32, 0.4], color: "#6f8fa8", position: [TABLE_X + 1.1, TABLE_TOP + 0.16, TABLE_Z + 0.1] },
];

const BLOCK_SPECS: BlockSpec[] = BASE_BLOCKS.map((block) => {
  const size: [number, number, number] = [
    block.size[0] * BLOCK_SCALE,
    block.size[1] * BLOCK_SCALE,
    block.size[2] * BLOCK_SCALE,
  ];
  return {
    ...block,
    size,
    position: [
      TABLE_X + (block.position[0] - TABLE_X) * 0.8,
      TABLE_TOP + size[1] / 2,
      TABLE_Z + (block.position[2] - TABLE_Z) * 0.8,
    ],
  };
});

function settleBlocks(list: BlockSpec[]): BlockSpec[] {
  const order = [...list].sort((a, b) => a.position[1] - b.position[1]);
  const settled = new Map<number, BlockSpec>();
  const placed: BlockSpec[] = [];

  for (const block of order) {
    let bottom = TABLE_TOP;
    for (const other of placed) {
      const dx = Math.abs(other.position[0] - block.position[0]);
      const dz = Math.abs(other.position[2] - block.position[2]);
      const reachX = ((other.size[0] + block.size[0]) / 2) * 0.9;
      const reachZ = ((other.size[2] + block.size[2]) / 2) * 0.9;
      if (dx < reachX && dz < reachZ) {
        bottom = Math.max(bottom, other.position[1] + other.size[1] / 2);
      }
    }
    const next: BlockSpec = {
      ...block,
      position: [block.position[0], bottom + block.size[1] / 2, block.position[2]],
    };
    settled.set(block.id, next);
    placed.push(next);
  }

  return list.map((block) => settled.get(block.id) ?? block);
}

function BlockGeometry({ shape, size }: { shape: BlockShape; size: [number, number, number] }) {
  if (shape === "cylinder") {
    return <cylinderGeometry args={[size[0] / 2, size[0] / 2, size[1], 24]} />;
  }
  if (shape === "cone") {
    return <coneGeometry args={[size[0] / 2, size[1], 24]} />;
  }
  if (shape === "sphere") {
    return <sphereGeometry args={[size[0] / 2, 24, 18]} />;
  }
  if (shape === "tetra") {
    return <coneGeometry args={[size[0] / 2, size[1], 4]} />;
  }
  return <boxGeometry args={size} />;
}

function BlockVisual({ block }: { block: BlockSpec }) {
  const material = (
    <meshStandardMaterial
      color={block.color}
      roughness={0.72}
      metalness={0.05}
      emissive={block.color}
      emissiveIntensity={0.05}
    />
  );

  if (block.shape === "box") {
    return (
      <RoundedBox
        args={block.size}
        radius={0.03}
        smoothness={3}
        castShadow
        receiveShadow
      >
        {material}
      </RoundedBox>
    );
  }

  return (
    <mesh castShadow receiveShadow>
      <BlockGeometry shape={block.shape} size={block.size} />
      {material}
    </mesh>
  );
}

function BlockTable({
  accent,
  onSelect,
}: {
  accent: string;
  onSelect: (id: HotspotId) => void;
}) {
  const [blocks, setBlocks] = useState(BLOCK_SPECS);
  const [dragging, setDragging] = useState<number | null>(null);
  const groupRefs = useRef<Record<number, Group | null>>({});
  const grabOffset = useRef(new Vector3());
  const controls = useThree((state) => state.controls) as any;
  const { camera, raycaster, pointer, scene } = useThree();
  const plane = useMemo(() => new Plane(new Vector3(0, 1, 0), -TABLE_TOP), []);

  const dropBlock = useCallback(
    (id: number) => {
      setBlocks((prev) => {
        const moved = prev.map((block) => {
          if (block.id !== id) return block;
          const group = groupRefs.current[block.id];
          if (!group) return block;
          return {
            ...block,
            position: [group.position.x, group.position.y, group.position.z] as [
              number,
              number,
              number,
            ],
          };
        });

        const settled = settleBlocks(moved);
        settled.forEach((block) => {
          const group = groupRefs.current[block.id];
          if (!group) return;
          group.userData.targetY = block.position[1];
          group.position.y = block.position[1];
        });
        return settled;
      });

      setDragging(null);
      if (controls) controls.enabled = true;
    },
    [controls]
  );

  useEffect(() => {
    const release = () => {
      if (dragging === null) return;
      if (document.pointerLockElement) return;
      dropBlock(dragging);
    };
    window.addEventListener("pointerup", release);
    return () => window.removeEventListener("pointerup", release);
  }, [dragging, dropBlock]);

  useEffect(() => {
    const onDown = (event: MouseEvent) => {
      if (!document.pointerLockElement || event.button !== 0) return;

      if (dragging !== null) {
        dropBlock(dragging);
        return;
      }

      raycaster.setFromCamera(new Vector2(0, 0), camera);
      const hits = raycaster.intersectObjects(scene.children, true);
      for (const hit of hits) {
        let current: Object3D | null = hit.object;
        while (current) {
          const hotspot = current.userData?.hotspot as HotspotId | undefined;
          if (hotspot) {
            onSelect(hotspot);
            return;
          }
          const blockId = current.userData?.blockId as number | undefined;
          if (typeof blockId === "number") {
            setDragging(blockId);
            return;
          }
          current = current.parent;
        }
      }
    };
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [camera, raycaster, scene, dragging, dropBlock, onSelect]);

  useEffect(() => {
    const onLockChange = () => {
      if (!document.pointerLockElement && dragging !== null) {
        dropBlock(dragging);
      }
    };
    document.addEventListener("pointerlockchange", onLockChange);
    return () => document.removeEventListener("pointerlockchange", onLockChange);
  }, [dragging, dropBlock]);

  useFrame(() => {
    if (dragging !== null) {
      const group = groupRefs.current[dragging];
      const current = blocks.find((item) => item.id === dragging);
      if (!group || !current) return;

      let targetX = group.position.x;
      let targetZ = group.position.z;
      let snappedSupport: number | null = null;

      const rayOrigin = document.pointerLockElement ? new Vector2(0, 0) : pointer;
      raycaster.setFromCamera(rayOrigin, camera);
      const hits = raycaster.intersectObjects(scene.children, true);

      for (const hit of hits) {
        let cursor: Object3D | null = hit.object;
        let isSelf = false;
        while (cursor) {
          if (cursor === group) {
            isSelf = true;
            break;
          }
          cursor = cursor.parent;
        }
        if (isSelf) continue;

        let node: Object3D | null = hit.object;
        while (node) {
          const otherId = node.userData?.blockId as number | undefined;
          if (typeof otherId === "number" && otherId !== current.id) {
            const otherGroup = groupRefs.current[otherId];
            const other = blocks.find((item) => item.id === otherId);
            if (otherGroup && other) {
              targetX = otherGroup.position.x;
              targetZ = otherGroup.position.z;
              snappedSupport = otherGroup.position.y + other.size[1] / 2;
            }
            break;
          }
          node = node.parent;
        }
        if (snappedSupport !== null) break;
      }

      if (snappedSupport === null) {
        if (document.pointerLockElement) {
          const direction = new Vector3();
          camera.getWorldDirection(direction);
          let distance = 2.4;
          if (direction.y < -0.08) {
            distance = (TABLE_TOP - camera.position.y) / direction.y;
          }
          distance = Math.min(Math.max(distance, 0.8), 4.5);
          const point = camera.position.clone().addScaledVector(direction, distance);
          targetX = point.x;
          targetZ = point.z;
        } else {
          raycaster.setFromCamera(pointer, camera);
          const hit = new Vector3();
          if (!raycaster.ray.intersectPlane(plane, hit)) return;
          targetX = hit.x - grabOffset.current.x;
          targetZ = hit.z - grabOffset.current.z;
        }
      }

      const dx = targetX - TABLE_X;
      const dz = targetZ - TABLE_Z;
      const radius = Math.hypot(dx, dz);
      const limit = 1.75;
      const factor = radius > limit ? limit / radius : 1;
      const finalX = TABLE_X + dx * factor;
      const finalZ = TABLE_Z + dz * factor;

      let support = snappedSupport ?? TABLE_TOP;
      if (snappedSupport === null) {
        let bestScore = Number.POSITIVE_INFINITY;
        for (const other of blocks) {
          if (other.id === current.id) continue;
          const ox = Math.abs(other.position[0] - finalX);
          const oz = Math.abs(other.position[2] - finalZ);
          const reachX = ((other.size[0] + current.size[0]) / 2) * 0.9;
          const reachZ = ((other.size[2] + current.size[2]) / 2) * 0.9;
          if (ox < reachX && oz < reachZ) {
            const score = ox / reachX + oz / reachZ;
            if (score < bestScore) {
              bestScore = score;
              const otherGroup = groupRefs.current[other.id];
              const otherY = otherGroup ? otherGroup.position.y : other.position[1];
              support = otherY + other.size[1] / 2;
            }
          }
        }
      }

      group.position.x = finalX;
      group.position.z = finalZ;
      group.position.y = support + current.size[1] / 2 + 0.06;
      return;
    }

    for (const block of blocks) {
      const group = groupRefs.current[block.id];
      const target = group?.userData.targetY as number | undefined;
      if (!group || target === undefined) continue;
      group.position.y += (target - group.position.y) * 0.4;
      if (Math.abs(group.position.y - target) < 0.001) {
        group.position.y = target;
      }
    }
  });

  return (
    <>
      <mesh position={[TABLE_X, 0.9, TABLE_Z]} receiveShadow>
        <cylinderGeometry args={[2, 2.1, 0.12, 48]} />
        <meshStandardMaterial color="#3a2a22" roughness={0.9} metalness={0.04} />
      </mesh>
      <mesh position={[TABLE_X, TABLE_TOP + 0.01, TABLE_Z]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.82, 2.0, 64]} />
        <meshBasicMaterial color={accent} transparent opacity={0.5} />
      </mesh>
      {blocks.map((block) => (
        <group
          key={block.id}
          ref={(node) => {
            groupRefs.current[block.id] = node;
          }}
          position={block.position}
          userData={{ blockId: block.id, height: block.size[1], targetY: block.position[1] }}
        >
          <mesh
            scale={1.3}
            onPointerDown={(event) => {
              event.stopPropagation();
              const group = groupRefs.current[block.id];
              if (group) {
                grabOffset.current.set(
                  event.point.x - group.position.x,
                  0,
                  event.point.z - group.position.z
                );
              }
              setDragging(block.id);
              if (controls) controls.enabled = false;
            }}
          >
            <BlockGeometry shape={block.shape} size={block.size} />
            <meshBasicMaterial transparent opacity={0} depthWrite={false} />
          </mesh>
          <BlockVisual block={block} />
        </group>
      ))}
      <Html
        center
        distanceFactor={11}
        position={[TABLE_X, 1.55, TABLE_Z]}
        wrapperClass="hotspot-tag-wrap"
      >
        <div className="hotspot-tag">自由搭建</div>
      </Html>
    </>
  );
}

const SHARDS: { position: [number, number, number]; phase: number; scale: number }[] = [
  { position: [-6.4, 1.5, -4.2], phase: 0.4, scale: 1.0 },
  { position: [6.2, 2.1, -5.4], phase: 1.7, scale: 0.8 },
  { position: [-7.1, 2.4, 2.6], phase: 2.9, scale: 1.15 },
  { position: [5.6, 1.3, 4.4], phase: 4.1, scale: 0.75 },
  { position: [-2.6, 2.8, -6.4], phase: 5.2, scale: 0.65 },
  { position: [2.9, 1.9, 6.2], phase: 0.9, scale: 0.85 },
];

const BEAMS: { position: [number, number, number]; height: number }[] = [
  { position: [-7.4, 0, -7.2], height: 3.6 },
  { position: [7.2, 0, -6.6], height: 3.2 },
  { position: [-6.8, 0, 6.4], height: 2.8 },
];

export default function RoomScene({
  level,
  onSelect,
  active,
}: {
  level: RiskLevel;
  onSelect: (id: HotspotId) => void;
  active: HotspotId | null;
}) {
  const palette = PALETTE[level];

  return (
    <>
      <fog attach="fog" args={[palette.fog, palette.fogNear, palette.fogFar]} />
      <ambientLight intensity={0.42} color="#8fa6d8" />
      <directionalLight
        position={[5, 8, 5]}
        intensity={1.15}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
        shadow-bias={-0.0004}
      />
      <pointLight
        position={[0, 4.2, 0]}
        intensity={palette.light}
        distance={26}
        color={palette.accent}
      />
      <pointLight position={[0, 1.4, -4]} intensity={6} distance={12} color={palette.accent} />

      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[20, 20]} />
        <meshStandardMaterial color={palette.floor} roughness={1} />
      </mesh>

      <mesh position={[0, 2, -9.02]}>
        <planeGeometry args={[20, 4]} />
        <meshStandardMaterial color={palette.wall} roughness={1} />
      </mesh>
      <mesh position={[-9.02, 2, 0]} rotation={[0, Math.PI / 2, 0]}>
        <planeGeometry args={[18, 4]} />
        <meshStandardMaterial color={palette.wall} roughness={1} />
      </mesh>
      <mesh position={[9.02, 2, 0]} rotation={[0, -Math.PI / 2, 0]}>
        <planeGeometry args={[18, 4]} />
        <meshStandardMaterial color={palette.wall} roughness={1} />
      </mesh>

      <GroundRings color={palette.accent} />

      <BreathingOrb
        color={palette.accent}
        speed={palette.breath}
        active={active === "breathing"}
        onSelect={() => onSelect("breathing")}
      />

      <group userData={{ hotspot: "board" }}>
        <AbstractPanel
          position={[-5, 2.05, -8.86]}
          color={palette.accent}
          active={active === "board"}
          onSelect={() => onSelect("board")}
        />
        <HotspotNode
          position={[-5, 1.1, -8.5]}
          color={palette.accent}
          phase={0}
          label="评估依据"
          active={active === "board"}
          onSelect={() => onSelect("board")}
        />
      </group>

      <group userData={{ hotspot: "window" }}>
        <LightGate
          position={[5, 1.4, -8.86]}
          color={palette.accent}
          active={active === "window"}
          onSelect={() => onSelect("window")}
        />
        <HotspotNode
          position={[5, 1.1, -8.5]}
          color={palette.accent}
          phase={1.2}
          label="环境感知"
          active={active === "window"}
          onSelect={() => onSelect("window")}
        />
      </group>

      <group userData={{ hotspot: "shelf" }}>
        <MemoryPillar
          position={[7.4, 0, 2]}
          color={palette.accent}
          active={active === "shelf"}
          onSelect={() => onSelect("shelf")}
        />
        <HotspotNode
          position={[7.4, 1.85, 2]}
          color={palette.accent}
          phase={2.4}
          label="项目说明"
          active={active === "shelf"}
          onSelect={() => onSelect("shelf")}
        />
      </group>

      {SHARDS.map((shard) => (
        <FloatingShard
          key={`${shard.position[0]}-${shard.position[2]}`}
          position={shard.position}
          phase={shard.phase}
          scale={shard.scale}
          color={palette.accent}
        />
      ))}

      {BEAMS.map((beam) => (
        <LightBeam
          key={`${beam.position[0]}-${beam.position[2]}`}
          position={beam.position}
          height={beam.height}
          color={palette.accent}
        />
      ))}

      <BlockTable accent={palette.accent} onSelect={onSelect} />

      <Sparkles
        count={palette.particles}
        scale={[16, 3.6, 16]}
        size={2.6}
        speed={0.35}
        color={palette.accent}
        opacity={0.5}
      />
    </>
  );
}