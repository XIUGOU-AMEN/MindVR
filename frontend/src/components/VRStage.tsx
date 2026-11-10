import { useCallback, useEffect, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { XR, createXRStore } from "@react-three/xr";
import * as THREE from "three";
import type { AnalysisResult } from "../types";
import { RISK_META } from "../types";
import RoomScene, { type HotspotId } from "./Scene";

const store = createXRStore();

interface Props {
  result: AnalysisResult | null;
  onExit: () => void;
}

const HOTSPOT_TITLES: Record<HotspotId, string> = {
  breathing: "呼吸引导",
  board: "评估依据",
  window: "环境感知",
  shelf: "项目说明",
};

function WalkControls({
  onUnlock,
}: {
  onUnlock: (position: THREE.Vector3, direction: THREE.Vector3) => void;
}) {
  const { camera } = useThree();
  const keys = useRef<Record<string, boolean>>({});
  const yaw = useRef(0);
  const pitch = useRef(0);
  const eyeHeight = useRef(1.65);

  useEffect(() => {
    const euler = new THREE.Euler().setFromQuaternion(camera.quaternion, "YXZ");
    yaw.current = euler.y;
    pitch.current = euler.x;
    camera.rotation.order = "YXZ";
    camera.rotation.set(pitch.current, yaw.current, 0, "YXZ");

    const startedAt = performance.now();

    const onMove = (event: MouseEvent) => {
      if (!document.pointerLockElement) return;
      if (performance.now() - startedAt < 250) return;
      const movementX = THREE.MathUtils.clamp(event.movementX, -120, 120);
      const movementY = THREE.MathUtils.clamp(event.movementY, -120, 120);
      yaw.current -= movementX * 0.0022;
      pitch.current = THREE.MathUtils.clamp(
        pitch.current - movementY * 0.0022,
        -1.45,
        1.45
      );
      camera.rotation.y = yaw.current;
      camera.rotation.x = pitch.current;
    };

    const onLockChange = () => {
      if (!document.pointerLockElement) {
        const direction = new THREE.Vector3();
        camera.getWorldDirection(direction);
        onUnlock(camera.position.clone(), direction);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      keys.current[event.code] = true;
    };
    const onKeyUp = (event: KeyboardEvent) => {
      keys.current[event.code] = false;
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("pointerlockchange", onLockChange);
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("pointerlockchange", onLockChange);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [camera, onUnlock]);

  useFrame((_, delta) => {
    const forward = new THREE.Vector3(-Math.sin(yaw.current), 0, -Math.cos(yaw.current));
    const right = new THREE.Vector3(Math.cos(yaw.current), 0, -Math.sin(yaw.current));

    const move = new THREE.Vector3();
    if (keys.current.KeyW) move.add(forward);
    if (keys.current.KeyS) move.sub(forward);
    if (keys.current.KeyA) move.sub(right);
    if (keys.current.KeyD) move.add(right);

    if (move.lengthSq() > 0) {
      move.normalize().multiplyScalar(3.0 * delta);
      camera.position.add(move);
    }

    if (keys.current.KeyQ) {
      eyeHeight.current = Math.max(0.8, eyeHeight.current - 1.6 * delta);
    }
    if (keys.current.KeyE) {
      eyeHeight.current = Math.min(2.8, eyeHeight.current + 1.6 * delta);
    }
    if (keys.current.KeyR) {
      eyeHeight.current = 1.65;
    }

    camera.position.y += (eyeHeight.current - camera.position.y) * 0.25;
    camera.position.x = THREE.MathUtils.clamp(camera.position.x, -8.2, 8.2);
    camera.position.z = THREE.MathUtils.clamp(camera.position.z, -8.2, 8.2);
  });

  return null;
}

export default function VRStage({ result, onExit }: Props) {
  const [active, setActive] = useState<HotspotId | null>(null);
  const [walk, setWalk] = useState(false);
  const [notice, setNotice] = useState("");
  const [orbitTarget, setOrbitTarget] = useState<[number, number, number]>([0, 1.6, 0]);
  const [vrSupported, setVrSupported] = useState<boolean | null>(null);
  const [canvasKey, setCanvasKey] = useState(0);
  const controlsRef = useRef<any>(null);

  useEffect(() => {
    let cancelled = false;
    const xr = (navigator as Navigator & {
      xr?: { isSessionSupported?: (mode: string) => Promise<boolean> };
    }).xr;
    if (!xr?.isSessionSupported) {
      setVrSupported(false);
      return;
    }
    xr.isSessionSupported("immersive-vr")
      .then((supported) => {
        if (!cancelled) setVrSupported(supported);
      })
      .catch(() => {
        if (!cancelled) setVrSupported(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const level = result?.risk_level ?? "normal";
  const meta = RISK_META[level];
  const score = result?.phq8_score_estimation ?? 0;
  const probability = result?.depression_probability ?? 0;

  const handleUnlock = useCallback(
    (position: THREE.Vector3, direction: THREE.Vector3) => {
      setOrbitTarget([
        position.x + direction.x * 4,
        THREE.MathUtils.clamp(position.y + direction.y * 4, 0.8, 3.0),
        position.z + direction.z * 4,
      ]);
      setWalk(false);
    },
    []
  );

  function enterWalk() {
    const canvas = document.querySelector("canvas");
    if (!canvas) return;

    setNotice("");
    setActive(null);
    setWalk(true);

    try {
      canvas.requestPointerLock();
    } catch {
      setWalk(false);
      setNotice("当前浏览器不支持指针锁定，漫游无法启动。");
      return;
    }

    window.setTimeout(() => {
      if (document.pointerLockElement !== canvas) {
        setWalk(false);
        setNotice("鼠标锁定被拒绝，请点击画面后重试，或按 F11 全屏。");
      }
    }, 600);
  }

  function exitWalk() {
    if (document.pointerLockElement) {
      document.exitPointerLock();
      return;
    }
    setWalk(false);
  }

  async function enterVR() {
    setNotice("");
    if (vrSupported === false) {
      setNotice(
        "当前设备没有可用的 VR 头显。3D 场景仍可正常浏览，接入头显后可进入沉浸模式。"
      );
      return;
    }
    try {
      await store.enterVR();
    } catch {
      setNotice("进入 VR 失败，已恢复到桌面场景。请确认头显已连接并允许浏览器访问。");
      setCanvasKey((key) => key + 1);
    }
  }

  return (
    <div className="vr-root">
      <div className="vr-canvas">
        <Canvas key={canvasKey} camera={{ position: [0, 1.65, 6.5], fov: 55 }} shadows>
          <color attach="background" args={["#05070f"]} />
          <XR store={store}>
            <RoomScene level={level} onSelect={setActive} active={active} />
          </XR>
          {walk ? (
            <WalkControls onUnlock={handleUnlock} />
          ) : (
            <OrbitControls
              ref={controlsRef}
              enablePan={false}
              minPolarAngle={0.15}
              maxPolarAngle={Math.PI / 2 + 0.24}
              minDistance={1.5}
              maxDistance={7}
              target={orbitTarget}
            />
          )}
        </Canvas>
      </div>

      {walk && <div className="vr-crosshair" />}

      <div className="vr-overlay">
        <div className="vr-head">
          <div className="vr-label">
            <strong style={{ color: meta.color }}>{meta.label}</strong>
            <br />
            PHQ-8 估计 {score.toFixed(1)} / 24 · 模型风险概率 {(probability * 100).toFixed(1)}%
            <br />
            点击场景中的发光节点探索：呼吸引导 / 评估依据 / 环境感知 / 项目说明
          </div>
          {notice && <div className="vr-notice">{notice}</div>}
        </div>

        {active && (
          <aside className="hotspot-panel">
            <header className="hotspot-header">
              <span>{HOTSPOT_TITLES[active]}</span>
              <button className="panel-close" onClick={() => setActive(null)}>
                ×
              </button>
            </header>

            <div className="hotspot-body">
              {active === "breathing" && (
                <>
                  <p>跟随中央光球的节奏练习：吸气 4 秒、屏息 1 秒、呼气 6 秒。</p>
                  <p>
                    当前场景呼吸频率为 <strong>{paletteHint(level)}</strong>。
                    风险等级越高，越适合主动放慢节律。
                  </p>
                </>
              )}

              {active === "board" && (
                <>
                  {result?.evidence.length ? (
                    <ul className="hotspot-list">
                      {result.evidence.map((item) => (
                        <li key={item.feature}>
                          <span>{item.label_zh}</span>
                          <span className={item.direction === "up" ? "up" : "down"}>
                            {item.direction === "up" ? "风险↑" : "风险↓"} {item.value.toFixed(2)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>还没有分析结果，先返回网页运行一次示例。</p>
                  )}
                </>
              )}

              {active === "window" && (
                <>
                  <p>场景光照、雾效与空气粒子都会随风险等级变化。</p>
                  <p>
                    当前等级：<strong style={{ color: meta.color }}>{meta.label}</strong>
                  </p>
                  <p>建议：{meta.hint}</p>
                </>
              )}

              {active === "shelf" && (
                <>
                  <p>MindVR 是多模态心理状态感知的学术研究演示，不构成医学诊断。</p>
                  <p>
                    模型版本：<strong>{result?.model_version ?? "未加载"}</strong>
                    <br />
                    大模型后端：<strong>{result?.llm_backend ?? "未连接"}</strong>
                  </p>
                  <p>仓库不含任何 DAIC-WOZ 原始数据。</p>
                </>
              )}
            </div>
          </aside>
        )}

        <div className="vr-actions">
          <button className="btn-primary" onClick={enterVR}>
            {vrSupported === false ? "VR 设备未检测到" : "进入 VR 模式"}
          </button>
          <button className="btn-ghost" onClick={walk ? exitWalk : enterWalk}>
            {walk ? "退出漫游（ESC）" : "漫游模式"}
          </button>
          <button className="btn-ghost" onClick={onExit}>
            返回网页
          </button>
        </div>

        <div className="vr-hint">
          {walk
            ? "WASD 移动 · Q/E 升降 · R 重置高度 · 鼠标转向 · ESC 退出漫游"
            : "拖动旋转 · 滚轮缩放 · 点击节点探索 · 左前方按住积木可自由搭建"}
        </div>
      </div>
    </div>
  );
}

function paletteHint(level: string): string {
  if (level === "normal") return "舒缓";
  if (level === "mild") return "偏缓";
  if (level === "moderate") return "偏快";
  return "急促";
}