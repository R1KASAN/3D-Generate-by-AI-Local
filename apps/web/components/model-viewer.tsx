"use client";

import { Component, ComponentRef, ReactNode, Suspense, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { Environment, Html, OrbitControls, useGLTF } from "@react-three/drei";

interface ModelViewerProps {
  src: string;
  errorMessage?: string;
}

class ViewerErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <p role="alert">Model unavailable</p>;
    }
    return this.props.children;
  }
}

function LoadedModel({ src }: { src: string }) {
  const { scene } = useGLTF(src);
  return scene ? <primitive object={scene} /> : null;
}

export function ModelViewer({ src, errorMessage }: ModelViewerProps) {
  const controlsRef = useRef<ComponentRef<typeof OrbitControls>>(null);

  function rotateModel() {
    const controls = controlsRef.current;
    if (!controls) return;
    controls.setAzimuthalAngle(controls.getAzimuthalAngle() + Math.PI / 8);
    controls.update();
  }

  function zoomModel(direction: "in" | "out") {
    const controls = controlsRef.current;
    if (!controls) return;
    if (direction === "in") controls.dollyOut(1.2);
    else controls.dollyIn(1.2);
    controls.update();
  }

  return (
    <section role="region" aria-label="3D model viewer">
      <div role="toolbar" aria-label="Viewer controls">
        <button type="button" aria-label="Rotate" onClick={rotateModel}>
          Rotate
        </button>
        <button type="button" aria-label="Zoom in" onClick={() => zoomModel("in")}>
          Zoom in
        </button>
        <button type="button" aria-label="Zoom out" onClick={() => zoomModel("out")}>
          Zoom out
        </button>
        <button type="button" aria-label="Reset camera" onClick={() => controlsRef.current?.reset()}>
          Reset camera
        </button>
      </div>
      <p id="viewer-instructions">
        Drag to rotate, use the wheel or pinch to zoom, and right-drag or use two fingers to pan.
      </p>
      {errorMessage ? (
        <p role="alert">{errorMessage}</p>
      ) : (
        <div className="viewer-stage">
          <ViewerErrorBoundary>
            <Canvas camera={{ position: [0, 0, 3] }}>
              <ambientLight intensity={0.7} />
              <directionalLight position={[2, 2, 2]} intensity={1} />
              <Suspense fallback={<Html center>Loading model…</Html>}>
                <LoadedModel src={src} />
                <Environment preset="studio" />
              </Suspense>
              <OrbitControls
                ref={controlsRef}
                enablePan
                enableZoom
                enableRotate
              />
            </Canvas>
          </ViewerErrorBoundary>
        </div>
      )}
    </section>
  );
}
