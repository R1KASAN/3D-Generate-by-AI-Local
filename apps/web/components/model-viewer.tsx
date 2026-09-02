"use client";

import { Component, ComponentRef, ReactNode, Suspense, useRef, useState } from "react";
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
  const [interaction, setInteraction] = useState<"rotate" | "zoom" | "pan">("rotate");
  const controlsRef = useRef<ComponentRef<typeof OrbitControls>>(null);

  return (
    <section role="region" aria-label="3D model viewer">
      <div role="toolbar" aria-label="Viewer controls">
        <button type="button" aria-label="Rotate" aria-pressed={interaction === "rotate"} onClick={() => setInteraction("rotate")}>
          Rotate
        </button>
        <button type="button" aria-label="Zoom" aria-pressed={interaction === "zoom"} onClick={() => setInteraction("zoom")}>
          Zoom
        </button>
        <button type="button" aria-label="Pan" aria-pressed={interaction === "pan"} onClick={() => setInteraction("pan")}>
          Pan
        </button>
        <button type="button" aria-label="Reset camera" onClick={() => controlsRef.current?.reset()}>
          Reset camera
        </button>
      </div>
      {errorMessage ? (
        <p role="alert">{errorMessage}</p>
      ) : (
        <div data-interaction={interaction}>
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
                enablePan={interaction === "pan"}
                enableZoom={interaction === "zoom"}
                enableRotate={interaction === "rotate"}
              />
            </Canvas>
          </ViewerErrorBoundary>
        </div>
      )}
    </section>
  );
}
